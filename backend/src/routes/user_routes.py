from flask import Blueprint, jsonify, request

from database.database import (
    get_user_db,
    get_users_db,
    save_user_db,
    delete_user_db,
)

user_bp = Blueprint("users", __name__, url_prefix="/users")

@user_bp.get("")
def get_users():
    users = get_users_db("")

    if users is None:
        return jsonify({"error": "No users found by this name"}), 404

    response = []
    for user in users:
        response.append(user.to_dict())

    return jsonify(response)

@user_bp.get("/<int:user_id>")
def get_user(user_id):
    """
    Busca um usuário pelo id.
    ---
    tags:
      - Usuários
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: Usuário encontrado
      404:
        description: Usuário não encontrado
    """
    user = get_user_db(user_id)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict())


@user_bp.post("")
def create_user():
    """
    Cria um novo usuário.
    ---
    tags:
      - Usuários
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, password, email]
          properties:
            name: {type: string, example: "Maria"}
            password: {type: string, example: "senha123"}
            email: {type: string, example: "maria@email.com"}
    responses:
      201:
        description: Usuário criado (retorna o id)
    """
    body = request.get_json()

    user_id = save_user_db(
        body["name"],
        body["password"],
        body["email"],
    )

    return jsonify({"id": user_id}), 201


@user_bp.delete("/<int:user_id>")
def delete_user(user_id):
    """
    Remove um usuário pelo id.
    ---
    tags:
      - Usuários
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      204:
        description: Usuário removido
      404:
        description: Usuário não encontrado
    """
    if delete_user_db(user_id):
        return "", 204

    return jsonify({"error": "User not found"}), 404
