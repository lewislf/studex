from flask import Blueprint, jsonify, request

from database.database import (
    get_subject_db,
    get_deck_db,
    get_decks_db,
    save_deck_db,
    delete_deck_db,
    match_subject_user_db,
)

deck_bp = Blueprint("decks", __name__, url_prefix="/users/<int:user_id>/subjects/<int:subject_id>/decks")


@deck_bp.get("")
def get_decks(user_id, subject_id):
    """
    Lista todos os baralhos de uma matéria.
    ---
    tags:
      - Baralhos
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
    responses:
      200:
        description: Lista de baralhos encontrados
        schema:
          type: array
          items:
            type: object
            properties:
              id: {type: integer, description: "ID do baralho"}
              titulo: {type: string, description: "Título/Subtitle do baralho"}
              acuracia: {type: integer, description: "Acurácia em porcentagem"}
              creation_date: {type: string, format: "date-time", description: "Data de criação"}
              novos: {type: integer, description: "Quantidade de flashcards novos"}
              aprendendo: {type: integer, description: "Quantidade de flashcards em aprendizado"}
              review: {type: integer, description: "Quantidade de flashcards em revisão"}
              subject_id: {type: integer, description: "ID da matéria"}
              subject_name: {type: string, description: "Nome da matéria"}
      404:
        description: Usuário não possui a matéria ou nenhum baralho encontrado
    """
    decks = get_decks_db(subject_id)
    
    if decks is None:
        return jsonify({"error": "decks not found"}), 404
    
    subject = get_subject_db(subject_id)
    
    if subject is None:
        return jsonify({"error": "No subject has been found for this deck"}), 404
    
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    response = []
    for d in decks:
        deck = d.to_dict()
        deck = deck | {"subject_id": subject.id, "subject_name": subject.name,}
        response.append(deck)
           
    return jsonify(response)
        


@deck_bp.get("/<int:deck_id>")
def get_deck(user_id, subject_id, deck_id):
    """
    Busca um baralho específico pelo ID.
    ---
    tags:
      - Baralhos
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
        description: ID do baralho a ser buscado
    responses:
      200:
        description: Baralho encontrado
        schema:
          type: object
          properties:
            id: {type: integer, description: "ID do baralho"}
            titulo: {type: string, description: "Título do baralho"}
            acuracia: {type: integer, description: "Acurácia em porcentagem"}
            creation_date: {type: string, format: "date-time", description: "Data de criação"}
            novos: {type: integer, description: "Flashcards novos"}
            aprendendo: {type: integer, description: "Flashcards em aprendizado"}
            review: {type: integer, description: "Flashcards em revisão"}
            subject_id: {type: integer, description: "ID da matéria"}
            subject_name: {type: string, description: "Nome da matéria"}
      404:
        description: Usuário não possui a matéria ou baralho não encontrado
    """
    deck = get_deck_db(deck_id)
    
    if deck is None:
        return jsonify({"error": "deck not found"}), 404

    if subject_id != deck.subject_id:
        return jsonify({"error": "deck with id " + deck_id + "is not from this subject"}), 404
 
    subject = get_subject_db(deck.subject_id)

    if subject is None:
        return jsonify({"error": "deck has not been found"}), 404
    
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404


    return jsonify({"subject_id": subject.id, "subject_name": subject.name,} | deck.to_dict())



@deck_bp.post("")
def create_deck(user_id, subject_id):
    """
    Cria um novo baralho em uma matéria.
    ---
    tags:
      - Baralhos
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
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [subtitle, acuracy, new, learning, review, date]
          properties:
            subtitle: {type: string, example: "Baralho de Revisão 1", description: "Título/Subtitle do baralho"}
            acuracy: {type: integer, example: 0, description: "Acurácia inicial em porcentagem"}
            new: {type: integer, example: 0, description: "Quantidade de flashcards novos"}
            learning: {type: integer, example: 0, description: "Quantidade em aprendizado"}
            review: {type: integer, example: 0, description: "Quantidade em revisão"}
            date: {type: string, format: "date-time", example: "2026-07-07T10:00:00", description: "Data de criação"}
    responses:
      201:
        description: Baralho criado com sucesso
        schema:
          type: object
          properties:
            id: {type: integer, description: "ID do novo baralho"}
      404:
        description: Usuário não possui a matéria
    """
    body = request.get_json()

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    deck_id = save_deck_db(
        subject_id,
        body["subtitle"],
        body["acuracy"],
        body["new"],
        body["learning"],
        body["review"],
        body["date"]
    )

    return jsonify({"id": deck_id}), 201


@deck_bp.delete("/<int:deck_id>")
def delete_deck(user_id, subject_id, deck_id):
    """
    Deleta um baralho pelo ID.
    ---
    tags:
      - Baralhos
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
        description: ID do baralho a ser deletado
    responses:
      204:
        description: Baralho deletado com sucesso
      404:
        description: Usuário não possui a matéria ou baralho não encontrado
    """
    deck = get_deck_db(deck_id)

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    if deck is not None and subject_id != deck.subject_id:
        return jsonify({"error": "deck with id " + deck_id + "is not from this subject"}), 404

    if delete_deck_db(deck_id):
        return "", 204

    return jsonify({"error": "deck not found"}), 404
