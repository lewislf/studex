from datetime import date

from flask import Blueprint, jsonify, request

from database.database import (
    get_deck_db,
    get_flashcard_db,
    get_flashcards_db,
    save_flashcard_db,
    delete_flashcard_db,
    match_subject_user_db,
    update_flashcard_review_db,
    refresh_deck_counters_db,
    record_activity_db,
)
from srs import apply_review, RATINGS

flashcard_bp = Blueprint(
    "flashcards",
    __name__,
    url_prefix="/users/<int:user_id>/subjects/<int:subject_id>/decks/<int:deck_id>/flashcards",
)


@flashcard_bp.get("")
def get_flashcards(user_id, subject_id, deck_id):
    """
    Lista todos os flashcards de um baralho.
    ---
    tags:
      - Flashcards
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: ID do usuário
      - in: path
        name: subject_id
        type: integer
        required: true
        description: ID da matéria
      - in: path
        name: deck_id
        type: integer
        required: true
        description: ID do baralho
    responses:
      200:
        description: Lista de flashcards encontrados
        schema:
          type: array
          items:
            type: object
            properties:
              id: {type: integer, description: "ID do flashcard"}
              pergunta: {type: string, description: "Pergunta do flashcard"}
              resposta: {type: string, description: "Resposta do flashcard"}
              status: {type: string, description: "Status (novo, aprendendo, review, reaprendendo)"}
              deck_id: {type: integer, description: "ID do baralho"}
              deck_name: {type: string, description: "Nome do baralho"}
              subject_id: {type: integer, description: "ID da matéria"}
      404:
        description: Usuário não possui a matéria, baralho não encontrado, ou nenhum flashcard encontrado
    """
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    deck = get_deck_db(deck_id)

    if deck is None:
        return jsonify({"error": "deck not found"}), 404

    if deck.subject_id != subject_id:
        return jsonify({"error": "deck is not from this subject"}), 404

    flashcards = get_flashcards_db(deck_id)

    if flashcards is None:
        return jsonify({"error": "flashcards not found"}), 404

    response = []

    for f in flashcards:
        flashcard = f.to_dict()
        flashcard = flashcard | {
            "deck_id": deck.id,
            "deck_name": deck.titulo,
            "subject_id": subject_id,
        }
        response.append(flashcard)

    return jsonify(response)


@flashcard_bp.get("/<int:flashcard_id>")
def get_flashcard(user_id, subject_id, deck_id, flashcard_id):
    """
    Busca um flashcard específico pelo ID.
    ---
    tags:
      - Flashcards
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: ID do usuário
      - in: path
        name: subject_id
        type: integer
        required: true
        description: ID da matéria
      - in: path
        name: deck_id
        type: integer
        required: true
        description: ID do baralho
      - in: path
        name: flashcard_id
        type: integer
        required: true
        description: ID do flashcard a ser buscado
    responses:
      200:
        description: Flashcard encontrado
        schema:
          type: object
          properties:
            id: {type: integer, description: "ID do flashcard"}
            pergunta: {type: string, description: "Pergunta"}
            resposta: {type: string, description: "Resposta"}
            status: {type: string, description: "Status"}
            creation_date: {type: string, format: "date-time", description: "Data de criação"}
            deck_id: {type: integer, description: "ID do baralho"}
            deck_name: {type: string, description: "Nome do baralho"}
            subject_id: {type: integer, description: "ID da matéria"}
      404:
        description: Usuário não possui a matéria, baralho ou flashcard não encontrado
    """
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    deck = get_deck_db(deck_id)

    if deck is None:
        return jsonify({"error": "deck not found"}), 404

    if deck.subject_id != subject_id:
        return jsonify({"error": "deck is not from this subject"}), 404

    flashcard = get_flashcard_db(flashcard_id)

    if flashcard is None:
        return jsonify({"error": "flashcard not found"}), 404

    if flashcard.deck_id != deck_id:
        return jsonify({"error": "flashcard is not from this deck"}), 404

    return jsonify(
        {
            "deck_id": deck.id,
            "deck_name": deck.titulo,
            "subject_id": subject_id,
        }
        | flashcard.to_dict()
    )


@flashcard_bp.post("")
def create_flashcard(user_id, subject_id, deck_id):
    """
    Cria um novo flashcard em um baralho.
    ---
    tags:
      - Flashcards
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: ID do usuário
      - in: path
        name: subject_id
        type: integer
        required: true
        description: ID da matéria
      - in: path
        name: deck_id
        type: integer
        required: true
        description: ID do baralho
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [pergunta, resposta, status, creation_date]
          properties:
            pergunta: {type: string, example: "Qual é a capital do Brasil?", description: "Pergunta"}
            resposta: {type: string, example: "Brasília", description: "Resposta"}
            status: {type: string, enum: ["novo", "aprendendo", "review", "reaprendendo"], example: "novo", description: "Status inicial"}
            creation_date: {type: string, format: "date-time", example: "2026-07-07T10:00:00", description: "Data de criação"}
    responses:
      201:
        description: Flashcard criado com sucesso
        schema:
          type: object
          properties:
            id: {type: integer, description: "ID do novo flashcard"}
      404:
        description: Usuário não possui a matéria ou baralho não encontrado
    """
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    deck = get_deck_db(deck_id)

    if deck is None:
        return jsonify({"error": "deck not found"}), 404

    if deck.subject_id != subject_id:
        return jsonify({"error": "deck is not from this subject"}), 404

    body = request.get_json()

    flashcard_id = save_flashcard_db(
        deck_id,
        body["pergunta"],
        body["resposta"],
        body["status"],
        body["creation_date"],
    )

    return jsonify({"id": flashcard_id}), 201


@flashcard_bp.delete("/<int:flashcard_id>")
def delete_flashcard(user_id, subject_id, deck_id, flashcard_id):
    """
    Deleta um flashcard pelo ID.
    ---
    tags:
      - Flashcards
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: ID do usuário
      - in: path
        name: subject_id
        type: integer
        required: true
        description: ID da matéria
      - in: path
        name: deck_id
        type: integer
        required: true
        description: ID do baralho
      - in: path
        name: flashcard_id
        type: integer
        required: true
        description: ID do flashcard a ser deletado
    responses:
      204:
        description: Flashcard deletado com sucesso
      404:
        description: Usuário não possui a matéria, baralho ou flashcard não encontrado
    """
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    deck = get_deck_db(deck_id)

    if deck is None:
        return jsonify({"error": "deck not found"}), 404

    if deck.subject_id != subject_id:
        return jsonify({"error": "deck is not from this subject"}), 404

    flashcard = get_flashcard_db(flashcard_id)

    if flashcard is not None and flashcard.deck_id != deck_id:
        return jsonify({"error": "flashcard is not from this deck"}), 404

    if delete_flashcard_db(flashcard_id):
        return "", 204

    return jsonify({"error": "flashcard not found"}), 404


@flashcard_bp.post("/<int:flashcard_id>/review")
def review_flashcard(user_id, subject_id, deck_id, flashcard_id):
    """
    Registra a revisão de um flashcard (SRS) e agenda a próxima revisão.
    ---
    tags:
      - Flashcards
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: ID do usuário
      - in: path
        name: subject_id
        type: integer
        required: true
        description: ID da matéria
      - in: path
        name: deck_id
        type: integer
        required: true
        description: ID do baralho
      - in: path
        name: flashcard_id
        type: integer
        required: true
        description: ID do flashcard revisado
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [rating]
          properties:
            rating: {type: string, enum: ["reset", "dificil", "bom", "facil"], example: "bom", description: "Nota dada na revisão"}
    responses:
      200:
        description: Flashcard atualizado com o novo estado do SRS
        schema:
          type: object
          properties:
            id: {type: integer}
            status: {type: string}
            due_date: {type: string}
            interval_days: {type: number}
            ease: {type: number}
            reps: {type: integer}
            lapses: {type: integer}
      400:
        description: Rating inválido ou ausente
      404:
        description: Usuário não possui a matéria, baralho ou flashcard não encontrado
    """
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    deck = get_deck_db(deck_id)

    if deck is None:
        return jsonify({"error": "deck not found"}), 404

    if deck.subject_id != subject_id:
        return jsonify({"error": "deck is not from this subject"}), 404

    flashcard = get_flashcard_db(flashcard_id)

    if flashcard is None:
        return jsonify({"error": "flashcard not found"}), 404

    if flashcard.deck_id != deck_id:
        return jsonify({"error": "flashcard is not from this deck"}), 404

    body = request.get_json(silent=True) or {}
    rating = body.get("rating")

    if rating not in RATINGS:
        return jsonify({"error": f"invalid rating, expected one of {RATINGS}"}), 400

    status, due_date, interval_days, ease, reps, lapses = apply_review(
        flashcard, rating, today=date.today()
    )

    update_flashcard_review_db(
        flashcard_id, status, due_date, interval_days, ease, reps, lapses
    )
    refresh_deck_counters_db(deck_id)
    record_activity_db(user_id, date.today().isoformat())

    flashcard.status = status
    flashcard.due_date = due_date
    flashcard.interval_days = interval_days
    flashcard.ease = ease
    flashcard.reps = reps
    flashcard.lapses = lapses

    return jsonify(flashcard.to_dict())