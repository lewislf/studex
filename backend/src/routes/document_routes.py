import logging
import sys
from pathlib import Path
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request

from database.database import save_materials_db

logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).resolve().parent.parent / "rag_api"))
from search_query import load_documents, split_into_nodes, build_vector_index, COLLECTION_NAME
from materials import generate_materials

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
        description: Indexado, mas falha ao gerar ou salvar os materiais
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

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = DOCS_DIR / filename
    file.save(saved_path)

    id_user = request.form.get("user_id")

    if int(id_user) != user_id:
        return jsonify({"error": "Erro: O id do usuário passado na URL não corresponde ao ID passada na requisição"}), 400

    subject_id = request.form.get("subject_id")
    doc_metadata = {k: v for k, v in {"user_id": id_user, "subject_id": subject_id}.items() if v is not None}

    try:
        docs = load_documents([saved_path], metadata=doc_metadata)
        nodes = split_into_nodes(docs)
        build_vector_index(nodes, collection_name=COLLECTION_NAME)
    except Exception:
        logger.exception("Falha ao indexar documento %s", filename)
        return jsonify({"error": "Falha ao indexar o documento"}), 500

    try:
        materials = generate_materials(nodes, fallback_titulo=Path(filename).stem, subject_id=subject_id)
    except Exception:
        logger.exception("Falha ao gerar materiais para %s", filename)
        return jsonify({
            "filename": filename,
            "collection": COLLECTION_NAME,
            "status": "indexed_without_materials",
            "error": "Documento indexado, mas falha ao gerar os materiais de estudo",
        }), 207

    # Persiste os materiais na matéria escolhida (nova ou existente).
    # Sem subject_id, apenas devolve os materiais sem salvar.
    if subject_id is not None:
        try:
            save_materials_db(int(subject_id), materials)
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
