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


def _live_counters(user_id: int) -> dict:
    """
    Calcula os contadores do usuário ao vivo, agregando pelas matérias, em vez
    de ler o blob "counters" salvo na tabela users (que nunca é atualizado
    depois da criação da conta e sempre ficaria zerado).

    Sem uma fila de revisão de verdade (SRS) ainda, "pending_flashcards_today"
    e "total_flashcards_created" contam o mesmo total de flashcards criados.
    """
    subjects = get_subjects_db(user_id) or []

    summaries = 0
    mind_maps = 0
    flashcards = 0

    for subject in subjects:
        summaries += count_summaries_db(subject.id)
        mind_maps += count_mindmaps_db(subject.id)
        for deck in (get_decks_db(subject.id) or []):
            flashcards += count_flashcards_db(deck.id)

    return {
        "summaries": summaries,
        "mind_maps": mind_maps,
        "pending_flashcards_today": flashcards,
        "total_flashcards_created": flashcards,
    }

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
        data = user.to_dict()
        data["counters"] = _live_counters(user.id)
        response.append(data)

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

    data = user.to_dict()
    data["counters"] = _live_counters(user_id)
    return jsonify(data)


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

    data = user.to_dict()
    data["counters"] = _live_counters(user.id)
    return jsonify(data), 200


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
