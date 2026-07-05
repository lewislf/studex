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
    if delete_subject_db(subject_id):
        return "", 204

    return jsonify({"error": "Subject not found"}), 404
