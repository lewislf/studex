from flask import Blueprint, jsonify, request

from database.database import (
    get_user_db,
    get_users_db,
    save_user_db,
    delete_user_db,
)

user_bp = Blueprint("users", __name__, url_prefix="/users")


@user_bp.get("/<int:user_id>")
def get_user(user_id):
    user = get_user_db(user_id)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
    })


@user_bp.post("")
def create_user():
    body = request.get_json()

    user_id = save_user_db(
        body["name"],
        body["password"],
        body["email"],
    )

    return jsonify({"id": user_id}), 201


@user_bp.delete("/<int:user_id>")
def delete_user(user_id):
    if delete_user_db(user_id):
        return "", 204

    return jsonify({"error": "User not found"}), 404
