import logging
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from auth import create_token, require_auth
from database.database import (
    get_user_db,
    get_users_db,
    save_user_db,
    delete_user_db,
    login_user_db,
    get_subjects_db,
    count_summaries_db,
    count_mindmaps_db,
    count_due_flashcards_db,
    count_flashcards_by_user_db,
    get_activity_days_db,
    compute_streak,
)
from qdrant.qdrant_server import delete_vectors_by_metadata

logger = logging.getLogger(__name__)

user_bp = Blueprint("users", __name__, url_prefix="/users")

ACTIVITY_WINDOW_DAYS = 400


def _gamification_with_streak(user, base_gamification: dict | None) -> dict:
    """
    Injeta o streak real (calculado a partir de activity_days) no bloco de
    gamification do usuário. "streak" é duplicado de "current_streak" só
    por compatibilidade com o frontend atual.
    """
    today = date.today()
    since = (today - timedelta(days=ACTIVITY_WINDOW_DAYS)).isoformat()

    days = get_activity_days_db(user.id, since) or {}
    current_streak = compute_streak(set(days.keys()), today)

    return {
        **(base_gamification or {}),
        "current_streak": current_streak,
        "streak": current_streak,
    }


def _live_counters(user_id: int) -> dict:
    """
    Calcula os contadores do usuário ao vivo, agregando pelas matérias, em vez
    de ler o blob "counters" salvo na tabela users (que nunca é atualizado
    depois da criação da conta e sempre ficaria zerado).

    "pending_flashcards_today" é a fila de revisão SRS real: cards novos +
    cards vencidos (due_date <= hoje). "total_flashcards_created" é a
    contagem de todos os flashcards do usuário.
    """
    subjects = get_subjects_db(user_id) or []

    summaries = 0
    mind_maps = 0

    for subject in subjects:
        summaries += count_summaries_db(subject.id)
        mind_maps += count_mindmaps_db(subject.id)

    pending_flashcards_today = count_due_flashcards_db(user_id)
    total_flashcards_created = count_flashcards_by_user_db(user_id)

    return {
        "summaries": summaries,
        "mind_maps": mind_maps,
        "pending_flashcards_today": pending_flashcards_today,
        "total_flashcards_created": total_flashcards_created,
    }


@user_bp.get("")
@require_auth
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
        data["gamification"] = _gamification_with_streak(user, data.get("gamification"))
        response.append(data)

    return jsonify(response)

@user_bp.get("/<int:user_id>")
@require_auth
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
    data["gamification"] = _gamification_with_streak(user, data.get("gamification"))
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
    data["gamification"] = _gamification_with_streak(user, data.get("gamification"))
    data["token"] = create_token(user.id)
    return jsonify(data), 200


@user_bp.delete("/<int:user_id>")
@require_auth
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
        try:
            delete_vectors_by_metadata(user_id=user_id)
        except Exception:
            logger.exception("Falha ao limpar vetores órfãos do usuário %s no Qdrant", user_id)

        return "", 204

    return jsonify({"error": "User not found"}), 404


@user_bp.get("/<int:user_id>/activity")
@require_auth
def get_user_activity(user_id):
    """
    Atividade diária do usuário (streak/heatmap): dias em que revisou ao
    menos 1 flashcard ou enviou ao menos 1 arquivo.
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
        description: Dias ativos dos últimos 400 dias, streak atual e se hoje já conta como ativo
        schema:
          type: object
          properties:
            days: {type: object, example: {"2026-07-08": 3}}
            current_streak: {type: integer, example: 2}
            today_active: {type: boolean, example: true}
      404:
        description: Usuário não encontrado
    """
    user = get_user_db(user_id)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    today = date.today()
    since = (today - timedelta(days=ACTIVITY_WINDOW_DAYS)).isoformat()

    days = get_activity_days_db(user_id, since) or {}
    current_streak = compute_streak(set(days.keys()), today)

    return jsonify({
        "days": days,
        "current_streak": current_streak,
        "today_active": today.isoformat() in days,
    })
