from flask import Blueprint, jsonify, request

from routes.deck_routes import get_decks
from database.database import (
    count_flashcards_db,
    count_summaries_db,
    get_subject_db,
    get_subjects_db,
    get_decks_db,
    save_subject_db,
    delete_subject_db,
    match_subject_user_db,
)


subject_bp = Blueprint("subjects", __name__, url_prefix="/users/<int:user_id>/subjects")


@subject_bp.get("/<int:subject_id>")
def get_subject(user_id, subject_id):
    """
    Busca uma matéria pelo id.
    ---
    tags:
      - Matérias
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
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

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error:" "User does not have this subject!"}), 404

    decks = get_decks_db(subject_id)
    
    
    total_flashcards = 0
    if decks is not None:
        for deck in decks:
            total_flashcards += count_flashcards_db(deck.id)

    return jsonify(subject.to_dict() | {"total_topics": 11, "pending_in_queue": 10, "counters": {
                "summaries": count_summaries_db(subject_id),
                "mind_maps": 2,
                "flashcards": total_flashcards }
            })

@subject_bp.get("")
def get_subjects(user_id):
    """
    Lista as matérias de um usuário.
    ---
    tags:
      - Matérias
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: Id do usuário dono das matérias
    responses:
      200:
        description: Lista de matérias do usuário
      404:
        description: Nenhuma mat
    """
    subjects = get_subjects_db(user_id)

    if subjects is None:
        return jsonify({"error": "Subjects not found"}), 404
    

    # Estrutura a resposta e calcula a quantidade de flashcards
    response = [] 
    for subject in subjects:
        total_flashcards = 0
        decks = get_decks_db(subject.id,)
    
        if decks is not None:
            for deck in decks:
                total_flashcards += count_flashcards_db(deck.id,)
        
        response.append(subject.to_dict() | {"total_topics": 11, "pending_in_queue": 10, "counters": {
                "summaries": count_summaries_db(subject.id,),
                "mind_maps": 2,
                "flashcards": total_flashcards }
        })
        

    return jsonify(response)


@subject_bp.post("")
def create_subject(user_id):
    """
    Cria uma nova matéria para um usuário.
    ---
    tags:
      - Matérias
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, description, domain, icon, color, date]
          properties:
            user_id: {type: integer, example: 1}
            name: {type: string, example: "Redes de Computadores"}
            description: {type: string, example: "Camadas do modelo TCP/IP"}
            domain: {type: integer, example: 0}
            icon: {type: string, example: "globe"}
            color: {type: string, example: "#e63946"}
            date: {type: string, example: "2026-07-05"}
    responses:
      201:
        description: Matéria criada (retorna o id)
    """
    body = request.get_json()

    subject_id = save_subject_db(
        user_id,
        body["name"],
        body["description"],
        body["domain"],
        body["icon"],
        body["color"],
        body["date"],
    )

    return jsonify({"id": subject_id}), 201


@subject_bp.delete("/<int:subject_id>")
def delete_subject(user_id, subject_id):
    """
    Remove uma matéria pelo id.
    ---
    tags:
      - Matérias
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
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
    subject = get_subject_db(subject_id)

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error:" "User does not have this subject!"}), 404
    
    if subject is not None and user_id != subject.user_id:
        return jsonify({"error": "Mismatch between user_id from URL and user_id from subject"}), 404

    if delete_subject_db(subject_id):
        return "", 204

    return jsonify({"error": "Subject not found"}), 404
