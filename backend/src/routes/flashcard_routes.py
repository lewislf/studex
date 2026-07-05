from flask import Blueprint, jsonify, request

from database.database import (
    get_deck_db,
    get_flashcard_db,
    get_flashcards_db,
    save_flashcard_db,
    delete_flashcard_db,
    match_subject_user_db
)

flashcard_bp = Blueprint(
    "flashcards",
    __name__,
    url_prefix="/users/<int:user_id>/subjects/<int:subject_id>/decks/<int:deck_id>/flashcards",
)


@flashcard_bp.get("")
def get_flashcards(user_id, subject_id, deck_id):
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