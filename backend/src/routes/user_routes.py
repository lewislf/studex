import sqlite3

from flask import Blueprint, jsonify, request

from database.database import (
    get_user_db,
    get_users_db,
    save_user_db,
    delete_user_db,
    login_user_db,
)

user_bp = Blueprint("users", __name__, url_prefix="/users")

@user_bp.get("")
def get_users():
    """
    Busca todos os usuários do banco de dados.
    ---
    tags:
      - Usuários
    responses:
      200:
        description: Usuário encontrado
      404:
        description: Usuário não encontrado
    """
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
            gamification: {type: object, example: {"current_streak": 0, "active_yesterday": false}}
            counters: {type: object, example: {"summaries": 0, "mind_maps": 0, "pending_flashcards_today": 0, "total_flashcards_created": 0}}
    responses:
      201:
        description: Usuário criado (retorna o id)
      409:
        description: Email já cadastrado
    """
    body = request.get_json()

    try:
        user_id = save_user_db(
            body["name"],
            body["password"],
            body["email"],
            gamification=body.get("gamification"),
            counters=body.get("counters"),
        )
    except sqlite3.IntegrityError:
        # Coluna email é UNIQUE: cadastro duplicado retorna 409 em vez de estourar.
        return jsonify({"error": "Email já cadastrado"}), 409

    return jsonify({"id": user_id}), 201


@user_bp.post("/login")
def login_user():
    """
    Autentica um usuário por email e senha.
    ---
    tags:
      - Usuários
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string, example: "maria@email.com"}
            password: {type: string, example: "senha123"}
    responses:
      200:
        description: Autenticado (retorna id, name e email)
      400:
        description: Email ou senha ausentes
      401:
        description: Credenciais inválidas
    """
    body = request.get_json(silent=True) or {}

    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        return jsonify({"error": "Email e senha são obrigatórios"}), 400

    user = login_user_db(email, password)

    if user is None:
        return jsonify({"error": "Email ou senha inválidos"}), 401

    return jsonify(user.to_dict()), 200


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
