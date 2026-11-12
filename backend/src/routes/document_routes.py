import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Lock
from uuid import uuid4
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request

from auth import require_auth
from database.database import (
    save_materials_db,
    get_flashcards_by_subject_db,
    update_flashcard_embedding_db,
    match_subject_user_db,
    record_activity_db,
    get_summaries_db,
    get_mindmaps_db,
)

logger = logging.getLogger(__name__)

# Progresso do upload em andamento, por usuário (assume no máximo um upload
# ativo por vez por usuário). Não é persistido: só existe enquanto o request
# de upload está rodando, pro frontend acompanhar o estado real (não uma
# simulação) via GET /users/<id>/documents/progress.
# Cada upload recebe um token: dois uploads concorrentes do mesmo usuário não
# se sobrescrevem, e o finally de quem termina primeiro só limpa a entrada se
# ela ainda for a sua (senão apagaria o progresso do upload ainda rodando).
_progress_lock = Lock()
_progress_by_user: dict[int, dict] = {}


def _start_progress(user_id: int, filename: str, fases) -> str:
    """fases: quais materiais este upload pediu (MATERIAIS_VALIDOS ou um
    subconjunto), cada uma listada como False até on_phase_done marcá-la."""
    token = uuid4().hex
    with _progress_lock:
        state = {"token": token, "filename": filename}
        for fase in fases:
            state[fase] = False
        _progress_by_user[user_id] = state
    return token


def _mark_phase_done(user_id: int, nome: str, token: str) -> None:
    with _progress_lock:
        state = _progress_by_user.get(user_id)
        # nome fora das fases pedidas nesse upload (chave nem existe): ignora
        if state is not None and state["token"] == token and nome in state:
            state[nome] = True


def _clear_progress(user_id: int, token: str) -> None:
    with _progress_lock:
        state = _progress_by_user.get(user_id)
        if state is not None and state["token"] == token:
            _progress_by_user.pop(user_id, None)

sys.path.append(str(Path(__file__).resolve().parent.parent / "rag_api"))
from search_query import load_documents, split_into_nodes, build_vector_index, COLLECTION_NAME, embed_model
from materials import generate_materials, MATERIAIS_VALIDOS
from dedup import (
    deduplicar_flashcards,
    deve_criar_baralho,
    DEDUP_MIN_CARDS_NOVOS,
    filtrar_materiais_duplicados,
)

# getter do banco pra buscar os materiais já existentes na matéria, por tipo,
# no mesmo estilo que as rotas de summary/mindmap já usam (nenhuma função
# nova em database.py)
# lambdas (e não as funções direto): o nome é resolvido na hora da chamada,
# então substituir get_summaries_db/get_mindmaps_db neste módulo (ex.: em
# testes) tem efeito. Guardar a referência travava a função da importação.
_MATERIAL_DEDUP_GETTERS = {
    "resumo": lambda subject_id: get_summaries_db(subject_id),
    "mapa_mental": lambda subject_id: get_mindmaps_db(subject_id),
}


def _embed_textos(textos: list[str]) -> list[list[float]]:
    """Wrapper fino sobre o embed_model (bge-m3), injetado no dedup.
    Batch: uma única chamada pro Ollama em vez de uma por texto."""
    return embed_model.get_text_embedding_batch(textos)


def _dedup_baralho(materials: list[dict], subject_id: int, upload_ref: str) -> list[dict]:
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
            "Baralho descartado (upload %s, matéria %s): %d cards novos após dedup, mínimo é %d",
            upload_ref, subject_id, len(cards_dedup), DEDUP_MIN_CARDS_NOVOS,
        )
        return [m for m in materials if m["tipo"] != "baralho"]

    baralho["conteudo"]["flashcards"] = cards_dedup
    return materials


def _dedup_resumo_mapa(materials: list[dict], subject_id: int, upload_ref: str) -> list[dict]:
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
            "%s descartado (upload %s, matéria %s): duplicado de material já existente",
            tipo, upload_ref, subject_id,
        )
        resultado = [m for m in resultado if m["tipo"] != tipo]

    return resultado

document_bp = Blueprint("documents", __name__, url_prefix="/users/<int:user_id>/documents")

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
ALLOWED_EXTENSIONS = {".pdf"}


def _remove_stored_pdf(path: Path) -> None:
    """Apaga o PDF enviado (LGPD: limitação de armazenamento/finalidade; o
    conteúdo já foi indexado/processado). Nunca pode derrubar a requisição.
    Loga só o prefixo uuid (32 chars) do nome salvo; o resto é o nome
    original do usuário e nunca vai para o log."""
    ref = path.name[:32]
    try:
        path.unlink(missing_ok=True)
        logger.debug("PDF temporário removido: %s", ref)
    except Exception as exc:
        logger.warning("Falha ao remover PDF temporário %s: %s", ref, type(exc).__name__)


def cleanup_stale_uploads(max_age_hours: float = 24) -> int:
    """Rede de segurança: remove de DOCS_DIR arquivos mais velhos que
    max_age_hours (ex: sobras de um worker morto no meio do upload). Preserva
    apenas arquivos *.pdf (qualquer outro, ex: .gitkeep, fica). Devolve quantos arquivos foram removidos."""
    removidos = 0
    if not DOCS_DIR.is_dir():
        return 0
    limite = time.time() - max_age_hours * 3600
    for arquivo in DOCS_DIR.iterdir():
        try:
            if arquivo.suffix.lower() != ".pdf" or not arquivo.is_file():
                continue
            if arquivo.stat().st_mtime < limite:
                arquivo.unlink(missing_ok=True)
                removidos += 1
        except Exception as exc:
            logger.warning("Falha ao limpar arquivo antigo %s: %s", arquivo.name[:32], type(exc).__name__)
    return removidos


@document_bp.get("/progress")
@require_auth
def get_upload_progress(user_id):
    """
    Estado real do upload em andamento (se houver), pro frontend acompanhar
    o processamento sem simular etapas.
    ---
    tags:
      - Documentos
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: >
          "{active: false}" sem upload em andamento, ou "{active: true,
          filename, ...}" com o estado real de cada etapa pedida nesse
          upload (só as chaves entre resumo/mapa_mental/flashcards
          efetivamente solicitadas via 'materials' aparecem)
    """
    with _progress_lock:
        state = _progress_by_user.get(user_id)

    if state is None:
        return jsonify({"active": False})

    # token é só controle interno, não faz parte do estado exposto
    state = {k: v for k, v in state.items() if k != "token"}
    return jsonify({"active": True, **state})


@document_bp.post("")
@require_auth
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
      - in: formData
        name: materials
        type: string
        required: false
        description: >
          CSV com o subconjunto de materiais a gerar, dentre resumo,
          mapa_mental, flashcards. Ausente ou vazio gera os três.
    responses:
      201:
        description: Documento indexado e materiais gerados/salvos
      207:
        description: >
          Indexado, mas falha ao gerar ou salvar os materiais, ou (upload só
          de flashcards) os cards gerados eram todos duplicados dos já
          existentes na matéria
      400:
        description: Arquivo ausente, extensão inválida ou valor inválido em 'materials'
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

    # Campo opcional: CSV com o subconjunto de materiais a gerar. Ausente ou
    # vazio (string vazia) gera os três. Validado antes de salvar o PDF.
    materials_raw = request.form.get("materials")
    if materials_raw:
        tipos_pedidos = {t.strip() for t in materials_raw.split(",") if t.strip()}
        invalidos = tipos_pedidos - MATERIAIS_VALIDOS
        if invalidos:
            return jsonify({
                "error": (
                    f"Valores inválidos em 'materials': {', '.join(sorted(invalidos))}. "
                    f"Valores aceitos: {', '.join(sorted(MATERIAIS_VALIDOS))}."
                )
            }), 400
    else:
        tipos_pedidos = None  # None = gera os três (comportamento default)

    doc_metadata = {k: v for k, v in {"user_id": id_user, "subject_id": subject_id}.items() if v is not None}

    # Prefixo uuid no nome salvo em disco: dois uploads simultâneos do mesmo
    # arquivo (ex: "aula1.pdf") não colidem no mesmo path. O nome original
    # segue como sufixo só pra debug.
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    upload_ref = uuid4().hex  # id opaco do upload, usado nos logs (nome original pode ser dado pessoal)
    stored_filename = f"{upload_ref}_{filename}"
    saved_path = DOCS_DIR / stored_filename
    try:
        file.save(saved_path)
    except BaseException:
        # gravação parcial: não deixa arquivo órfão
        _remove_stored_pdf(saved_path)
        raise

    # Tudo após o save fica sob o try/finally: qualquer exceção (inclusive em
    # _start_progress) remove o PDF.
    token = None
    try:
        # Envio conta como atividade mesmo que a geração de materiais falhe
        # depois. Nunca pode derrubar o upload.
        try:
            record_activity_db(user_id, date.today().isoformat())
        except Exception:
            logger.exception("Falha ao registrar atividade de upload do usuário %s", user_id)

        token = _start_progress(user_id, filename, tipos_pedidos or MATERIAIS_VALIDOS)
        try:
            docs = load_documents([saved_path], metadata=doc_metadata)
            nodes = split_into_nodes(docs)
        except Exception as exc:
            # Só o tipo da exceção: a mensagem/traceback pode conter o caminho
            # do PDF (com o nome original, dado pessoal).
            logger.error("Falha ao ler/dividir documento (upload %s): %s", upload_ref, type(exc).__name__)
            return jsonify({"error": "Falha ao indexar o documento"}), 500

        index_error = None
        def _index():
            nonlocal index_error
            try:
                build_vector_index(nodes, collection_name=COLLECTION_NAME)
            except Exception as exc:
                index_error = exc
                logger.exception("Falha ao indexar documento (upload %s)", upload_ref)

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_index = executor.submit(_index)
                future_materials = executor.submit(
                    generate_materials,
                    nodes,
                    fallback_titulo=Path(filename).stem,
                    subject_id=subject_id,
                    on_phase_done=lambda nome: _mark_phase_done(user_id, nome, token),
                    tipos=tipos_pedidos,
                )
                materials = future_materials.result()
                future_index.result()
        except Exception:
            logger.exception("Falha ao gerar materiais (upload %s)", upload_ref)
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
                materials = _dedup_baralho(materials, subject_id, upload_ref)
            except Exception:
                # dedup não pode impedir de salvar resumo/mapa: loga e segue com
                # o baralho original se o dedup falhar
                logger.exception("Falha ao deduplicar flashcards para a matéria %s", subject_id)

            try:
                materials = _dedup_resumo_mapa(materials, subject_id, upload_ref)
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
                flashcards_only = tipos_pedidos == {"flashcards"}
                logger.info(
                    "Upload descartado por dedup: %s (matéria %s)",
                    upload_ref, subject_id,
                )
                return jsonify({
                    "filename": filename,
                    "collection": COLLECTION_NAME,
                    "subject_id": subject_id,
                    "status": "duplicate_flashcards" if flashcards_only else "duplicate_materials",
                    "error": (
                        "Os flashcards gerados são duplicados dos já existentes nesta "
                        "matéria; nenhum material novo foi salvo."
                    ) if flashcards_only else (
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
    finally:
        # O PDF sai PRIMEIRO: se _clear_progress levantar, o arquivo já foi
        # apagado (não é mais necessário após o processamento, sucesso ou falha).
        _remove_stored_pdf(saved_path)
        # Limpa o progresso independente do resultado, mas só se a entrada
        # ainda for deste upload (token bate); senão apagaria o progresso de
        # um upload concorrente do mesmo usuário ainda rodando.
        if token is not None:
            _clear_progress(user_id, token)
