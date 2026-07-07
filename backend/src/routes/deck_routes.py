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
    deck = get_deck_db(deck_id)

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    if deck is not None and subject_id != deck.subject_id:
        return jsonify({"error": "deck with id " + deck_id + "is not from this subject"}), 404

    if delete_deck_db(deck_id):
        return "", 204

    return jsonify({"error": "deck not found"}), 404
