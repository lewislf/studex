from flask import Blueprint, jsonify, request

from database.database import (
    count_summaries_db,
    get_deck_db,
    get_decks_db,
    save_deck_db,
    delete_deck_db,
)

deck_bp = Blueprint("decks", __name__, url_prefix="/decks")


@deck_bp.get("/<int:deck_id>")
def get_deck(deck_id):
    deck = get_deck_db(deck_id)
    subject = get_subject_db(deck.subject_id)

    if deck is None:
        return jsonify({"error": "deck not found"}), 404

    return jsonify({
        "subject_id": subject.id,
        "subject_name": subject.name,
        "subtitle": deck.titulo,
        "acuracy": deck.acuracy,
        "color": "#9b5de5",
        "date": deck.date,
        "new": deck.novos,
        "learning": deck.aprendendo,
        "review": deck.review,
        "total_cards": deck.novos + deck.aprendendo + deck.review
    })



@deck_bp.post("")
def create_deck():
    body = request.get_json()
    
    deck_id = save_deck_db(
        body["subject_id"],
        body["subtitle"],
        body["acuracy"],
        body["new"],
        body["learning"],
        body["review"],
        body["date"]
    )

    return jsonify({"id": deck_id}), 201


@deck_bp.delete("/<int:deck_id>")
def delete_deck(deck_id):
    if delete_deck_db(deck_id):
        return "", 204

    return jsonify({"error": "deck not found"}), 404
