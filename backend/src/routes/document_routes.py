import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request

from database.database import (
    save_materials_db,
    get_flashcards_by_subject_db,
    update_flashcard_embedding_db,
    match_subject_user_db,
    get_summaries_db,
    get_mindmaps_db,
)

logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).resolve().parent.parent / "rag_api"))
from search_query import load_documents, split_into_nodes, build_vector_index, COLLECTION_NAME, embed_model
from materials import generate_materials
from dedup import (
    deduplicar_flashcards,
    deve_criar_baralho,
    DEDUP_MIN_CARDS_NOVOS,
    filtrar_materiais_duplicados,
)

# getter do banco pra buscar os materiais já existentes na matéria, por tipo,
# no mesmo estilo que as rotas de summary/mindmap já usam (nenhuma função
# nova em database.py)
_MATERIAL_DEDUP_GETTERS = {
    "resumo": get_summaries_db,
    "mapa_mental": get_mindmaps_db,
}


def _embed_textos(textos: list[str]) -> list[list[float]]:
    """Wrapper fino sobre o embed_model (bge-m3), injetado no dedup.
    Batch: uma única chamada pro Ollama em vez de uma por texto."""
    return embed_model.get_text_embedding_batch(textos)


def _dedup_baralho(materials: list[dict], subject_id: int, filename: str) -> list[dict]:
    """
    Aplica o funil de deduplicação de flashcards (rag_api/dedup.py) no
    material tipo "baralho", se houver. Com menos de DEDUP_MIN_CARDS_NOVOS
    cards sobrando após o dedup, remove o baralho da lista de materiais
    (resumo e mapa mental seguem normal).
    """
    baralho = next((m for m in materials if m["tipo"] == "baralho"), None)
    if baralho is None:
        return materials

    cards_novos = baralho["conteudo"]["flashcards"]
    existentes = get_flashcards_by_subject_db(subject_id)

    cards_dedup = deduplicar_flashcards(
        cards_novos,
        existentes,
        embed_fn=_embed_textos,
        persist_embedding_fn=update_flashcard_embedding_db,
    )

    if not deve_criar_baralho(cards_dedup):
        logger.info(
            "Baralho descartado para %s (matéria %s): %d cards novos após dedup, mínimo é %d",
            filename, subject_id, len(cards_dedup), DEDUP_MIN_CARDS_NOVOS,
        )
        return [m for m in materials if m["tipo"] != "baralho"]

    baralho["conteudo"]["flashcards"] = cards_dedup
    return materials


def _dedup_resumo_mapa(materials: list[dict], subject_id: int, filename: str) -> list[dict]:
    """
    Aplica o dedup lexical (rag_api/dedup.py) aos materiais tipo "resumo" e
    "mapa_mental" contra os já existentes na matéria. Reenviar o mesmo PDF
    hoje não pode duplicar resumo/mapa mental (o dedup de baralho, acima, só
    cobre flashcards). Sem mudança de schema: busca os existentes com as
    mesmas funções que as rotas de summary/mindmap já usam.
    """
    resultado = list(materials)
    for tipo, getter in _MATERIAL_DEDUP_GETTERS.items():
        novo = next((m for m in resultado if m["tipo"] == tipo), None)
        if novo is None:
            continue

        existentes = getter(subject_id) or []
        if filtrar_materiais_duplicados([novo], existentes, tipo=tipo):
            continue  # sobreviveu ao dedup, mantém no resultado

        logger.info(
            "%s descartado para %s (matéria %s): duplicado de material já existente",
            tipo, filename, subject_id,
        )
        resultado = [m for m in resultado if m["tipo"] != tipo]

    return resultado


document_bp = Blueprint("documents", __name__, url_prefix="/users/<int:user_id>/documents")

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
ALLOWED_EXTENSIONS = {".pdf"}


@document_bp.post("")
def upload_document(user_id):
    """
    Envia um PDF, gera os materiais de estudo e os salva na matéria escolhida.
    ---
    tags:
      - Documentos
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Arquivo PDF
      - in: formData
        name: subject_id
        type: integer
        required: false
        description: Matéria (nova ou existente) onde salvar os materiais
      - in: formData
        name: user_id
        type: integer
        required: false
        description: Usuário dono do upload
    responses:
      201:
        description: Documento indexado e materiais gerados/salvos
      207:
        description: >
          Indexado, mas falha ao gerar ou salvar os materiais, ou todos os
          materiais gerados eram duplicados dos já existentes na matéria
      400:
        description: Arquivo ausente ou extensão inválida
      500:
        description: Falha ao indexar o documento
    """

    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado (campo 'file' ausente)"}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    filename = secure_filename(file.filename)
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Extensão não suportada: {extension}"}), 400

    # Valida user_id e subject_id ANTES de salvar o PDF em disco, pra não
    # deixar arquivo órfão quando a requisição está malformada.
    id_user_raw = request.form.get("user_id")
    try:
        id_user = int(id_user_raw)
    except (TypeError, ValueError):
        return jsonify({
            "error": "Campo 'user_id' ausente ou inválido. Envie o id numérico do usuário."
        }), 400

    if id_user != user_id:
        return jsonify({"error": "Erro: O id do usuário passado na URL não corresponde ao ID passada na requisição"}), 400

    subject_id = request.form.get("subject_id")
    # Valida se o id da matéria é inválido.
    if subject_id is not None:
        try:
            subject_id = int(subject_id)
        except (TypeError, ValueError):
            return jsonify({
                "error": f"subject_id inválido: '{subject_id}'. Envie o id numérico de uma matéria existente."
            }), 400

        # a matéria precisa ser do usuário que está fazendo o upload, senão
        # qualquer um grava material na matéria de outro usuário
        if not match_subject_user_db(subject_id, user_id):
            return jsonify({"error": "User does not have this subject!"}), 404

    doc_metadata = {k: v for k, v in {"user_id": id_user, "subject_id": subject_id}.items() if v is not None}

    # Prefixo uuid no nome salvo em disco: dois uploads simultâneos do mesmo
    # arquivo (ex: "aula1.pdf") não colidem no mesmo path. O nome original
    # segue como sufixo só pra debug.
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}_{filename}"
    saved_path = DOCS_DIR / stored_filename
    file.save(saved_path)

    try:
        docs = load_documents([saved_path], metadata=doc_metadata)
        nodes = split_into_nodes(docs)
    except Exception:
        logger.exception("Falha ao indexar documento %s", filename)
        return jsonify({"error": "Falha ao indexar o documento"}), 500

    index_error = None
    def _index():
        nonlocal index_error
        try:
            build_vector_index(nodes, collection_name=COLLECTION_NAME)
        except Exception as exc:
            index_error = exc
            logger.exception("Falha ao indexar documento %s", filename)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_index = executor.submit(_index)
            future_materials = executor.submit(
                generate_materials,
                nodes,
                fallback_titulo=Path(filename).stem,
                subject_id=subject_id,
            )
            materials = future_materials.result()
            future_index.result()
    except Exception:
        logger.exception("Falha ao gerar materiais para %s", filename)
        return jsonify({
            "filename": filename,
            "collection": COLLECTION_NAME,
            "status": "indexed_without_materials",
            "error": "Documento indexado, mas falha ao gerar os materiais de estudo",
        }), 207

    if index_error is not None:
        return jsonify({"error": "Falha ao indexar o documento"}), 500

    # Persiste os materiais na matéria escolhida (nova ou existente).
    # Sem subject_id, apenas devolve os materiais sem salvar.
    if subject_id is not None:
        tinha_materiais_antes_do_dedup = bool(materials)
        try:
            materials = _dedup_baralho(materials, subject_id, filename)
        except Exception:
            # dedup não pode impedir de salvar resumo/mapa: loga e segue com
            # o baralho original se o dedup falhar
            logger.exception("Falha ao deduplicar flashcards para a matéria %s", subject_id)

        try:
            materials = _dedup_resumo_mapa(materials, subject_id, filename)
        except Exception:
            # mesmo princípio: dedup de resumo/mapa não pode impedir salvar
            logger.exception("Falha ao deduplicar resumo/mapa mental para a matéria %s", subject_id)

        # Caso especial: TODOS os materiais que a geração de fato produziu
        # foram descartados por dedup (duplicados dos já existentes na
        # matéria, ou baralho abaixo do mínimo de cards novos). Sem essa
        # checagem, cairia no fluxo normal e salvaria uma matéria "vazia"
        # silenciosamente. Sem nada descartado por dedup (ex. LLM falhou
        # antes do dedup entrar), materials já estava vazio antes, então
        # tinha_materiais_antes_do_dedup é False e cai no fluxo normal.
        if tinha_materiais_antes_do_dedup and not materials:
            logger.info(
                "Upload descartado por dedup: %s (matéria %s)",
                filename, subject_id,
            )
            return jsonify({
                "filename": filename,
                "collection": COLLECTION_NAME,
                "subject_id": subject_id,
                "status": "duplicate_materials",
                "error": (
                    "Os materiais gerados são duplicados dos já existentes nesta "
                    "matéria; nenhum material novo foi salvo."
                ),
            }), 207

        try:
            save_materials_db(subject_id, materials)
        except Exception:
            logger.exception("Falha ao salvar materiais para a matéria %s", subject_id)
            return jsonify({
                "filename": filename,
                "collection": COLLECTION_NAME,
                "status": "generated_without_saving",
                "error": "Materiais gerados, mas falha ao salvá-los na matéria",
                "materiais": materials,
            }), 207

    return jsonify({
        "filename": filename,
        "collection": COLLECTION_NAME,
        "subject_id": subject_id,
        "status": "indexed",
        "materiais": materials,
    }), 201
