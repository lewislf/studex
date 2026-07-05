from flask import Blueprint, jsonify, request

from database.database import (
    count_summaries_db,
    get_subject_db,
    get_subjects_db,
    get_subjects_by_user_db,
    save_subject_db,
    delete_subject_db,
)

subject_bp = Blueprint("subjects", __name__, url_prefix="/subjects")


@subject_bp.get("")
def list_subjects():
    """
    Lista as matérias de um usuário.
    ---
    tags:
      - Matérias
    parameters:
      - in: query
        name: user_id
        type: integer
        required: true
        description: Id do usuário dono das matérias
    responses:
      200:
        description: Lista de matérias do usuário
      400:
        description: Parâmetro user_id ausente
    """
    user_id = request.args.get("user_id")

    if user_id is None:
        return jsonify({"error": "Parâmetro 'user_id' é obrigatório"}), 400

    subjects = get_subjects_by_user_db(user_id)

    return jsonify([
        {
            "id": subject.id,
            "title": subject.name,
            "user_id": subject.user_id,
            "description": subject.description,
            "date": subject.date,
            "mastery_percentage": subject.domain,
        }
        for subject in subjects
    ])


@subject_bp.get("/<int:subject_id>")
def get_subject(subject_id):
    """
    Busca uma matéria pelo id.
    ---
    tags:
      - Matérias
    parameters:
      - in: path
        name: subject_id
        type: integer
        required: true
    responses:
      200:
        description: Matéria encontrada
      404:
        description: Matéria não encontrada
    """
    subject = get_subject_db(subject_id)

    if subject is None:
        return jsonify({"error": "Subject not found"}), 404

    return jsonify({
            "id": subject.id,
            "title": subject.name,
            "user_id": subject.user_id,
            "description": subject.description,
            "date": subject.date,
            "icon": "globe",
            "color": "#e63946",
            "total_topics": 11,
            "mastery_percentage": subject.domain,
            "pending_in_queue": 10,
            "counters": {
                "summaries": count_summaries_db(subject_id),
                "mind_maps": 2,
                "flashcards": 10
            }
        })



@subject_bp.post("")
def create_subject():
    """
    Cria uma nova matéria para um usuário.
    ---
    tags:
      - Matérias
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [user_id, name, description, domain, date]
          properties:
            user_id: {type: integer, example: 1}
            name: {type: string, example: "Redes de Computadores"}
            description: {type: string, example: "Camadas do modelo TCP/IP"}
            domain: {type: integer, example: 0}
            date: {type: string, example: "2026-07-05"}
    responses:
      201:
        description: Matéria criada (retorna o id)
    """
    body = request.get_json()

    subject_id = save_subject_db(
        body["user_id"],
        body["name"],
        body["description"],
        body["domain"],
        body["date"]
    )

    return jsonify({"id": subject_id}), 201


@subject_bp.delete("/<int:subject_id>")
def delete_subject(subject_id):
    """
    Remove uma matéria pelo id.
    ---
    tags:
      - Matérias
    parameters:
      - in: path
        name: subject_id
        type: integer
        required: true
    responses:
      204:
        description: Matéria removida
      404:
        description: Matéria não encontrada
    """
    if delete_subject_db(subject_id):
        return "", 204

    return jsonify({"error": "Subject not found"}), 404
