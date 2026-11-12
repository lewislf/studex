import logging
import re
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from auth import create_token, require_auth, require_admin
import rate_limit
from database.database import (
    get_user_db,
    get_users_db,
    save_user_db,
    delete_user_db,
    login_user_db,
    count_user_materials_db,
    count_due_flashcards_db,
    count_flashcards_by_user_db,
    get_activity_days_db,
    compute_streak,
)
from qdrant.qdrant_server import delete_vectors_by_metadata

logger = logging.getLogger(__name__)

user_bp = Blueprint("users", __name__, url_prefix="/users")

ACTIVITY_WINDOW_DAYS = 400

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
MAX_LOGIN_FIELD = 1024  # limita o custo do hash da senha no login


def _validate_signup(body):
    """Valida o corpo do cadastro. Retorna (dados_normalizados, None) ou (None, msg_erro)."""
    if not isinstance(body, dict):
        return None, "Corpo da requisição inválido. Envie um JSON com nome, email e senha."

    name, email, password = body.get("name"), body.get("email"), body.get("password")

    if not isinstance(name, str) or not name.strip():
        return None, "Informe seu nome."
    name = name.strip()
    if len(name) > 100:
        return None, "O nome deve ter no máximo 100 caracteres."

    if not isinstance(email, str) or not email.strip():
        return None, "Informe seu email."
    email = email.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        return None, "Email inválido."

    if not isinstance(password, str) or not password:
        return None, "Informe uma senha."
    if len(password) < 8:
        return None, "A senha deve ter ao menos 8 caracteres."
    if len(password) > 128:
        return None, "A senha deve ter no máximo 128 caracteres."

    return {"name": name, "email": email, "password": password}, None


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
    summaries, mind_maps = count_user_materials_db(user_id)

    pending_flashcards_today = count_due_flashcards_db(user_id)
    total_flashcards_created = count_flashcards_by_user_db(user_id)

    return {
        "summaries": summaries,
        "mind_maps": mind_maps,
        "pending_flashcards_today": pending_flashcards_today,
        "total_flashcards_created": total_flashcards_created,
    }


@user_bp.get("")
@require_admin
def get_users():
    """
    Lista todos os usuários (somente administradores, ADMIN_USER_IDS).
    ---
    tags:
      - Usuários
    responses:
      200:
        description: Lista de usuários (id, name, email, counters, gamification)
      401:
        description: Token ausente ou inválido
      403:
        description: Usuário autenticado não é administrador
    """
    users = get_users_db("")

    if users is None:
        return jsonify({"error": "No users found by this name"}), 404

    response = []
    for user in users:
        # campos explícitos, para não vazar o hash da senha
        response.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "counters": _live_counters(user.id),
            "gamification": _gamification_with_streak(user, user.gamification),
        })

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
    responses:
      201:
        description: Usuário criado (retorna o id)
      400:
        description: Corpo inválido (nome 1-100, email válido até 254, senha 8-128)
      429:
        description: Muitas tentativas de cadastro deste IP
      409:
        description: Email já cadastrado
    """
    body = request.get_json(silent=True)
    data, error = _validate_signup(body)
    if error:
        return jsonify({"error": error}), 400

    if rate_limit.enabled():
        # só cadastros válidos consomem cota (o custo é o hash argon2)
        cfg = rate_limit.limits()
        wait = rate_limit.limiter.check_and_record(
            rate_limit.mac_key("signup", rate_limit.client_ip()),
            cfg["signup_ip_max"], cfg["signup_window"],
        )
        if wait:
            logger.warning("rate limit: cadastro bloqueado por ip")
            return rate_limit.too_many(wait)

    try:
        # gamification/counters não vêm do cliente
        user_id = save_user_db(data["name"], data["password"], data["email"])
    except sqlite3.IntegrityError:
        # a mensagem permite enumerar contas; trade-off de UX
        return jsonify({"error": "Email já cadastrado"}), 409

    return jsonify({"id": user_id, "token": create_token(user_id)}), 201


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
      429:
        description: Muitas tentativas (por IP ou por conta); veja Retry-After
    """
    use_limit = rate_limit.enabled()
    cfg = rate_limit.limits() if use_limit else None

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}

    email = body.get("email")
    password = body.get("password")

    if (
        not isinstance(email, str) or not isinstance(password, str)
        or not email or not password
    ):
        return jsonify({"error": "Email e senha são obrigatórios"}), 400
    if len(email) > MAX_LOGIN_FIELD or len(password) > MAX_LOGIN_FIELD:
        return jsonify({"error": "Email ou senha inválidos"}), 400

    if use_limit:
        # Só falhas contam, por IP, por par e-mail+IP e por conta (qualquer IP).
        # Checagem e registro são separados: sob concorrência o limite pode
        # estourar em até o nº de threads.
        ip = rate_limit.client_ip()
        em = rate_limit.normalise_email(email)
        ip_key = rate_limit.mac_key("lip", ip)
        pair_key = rate_limit.mac_key("lpair", ip, em)
        acc_key = rate_limit.mac_key("lacc", em)
        win = cfg["login_window"]
        # Os limites valem antes da senha, mesmo para senha correta; senão o
        # 429 viraria um oráculo. Trade-off: quem errar a senha de uma conta a
        # partir de vários IPs consegue bloqueá-la enquanto continuar tentando.
        scopes = [
            ("ip", ip_key, cfg["login_ip_max"]),
            ("par", pair_key, cfg["login_pair_max"]),
            ("conta", acc_key, cfg["login_email_max"]),
        ]
        for nome, key, lim in scopes:
            wait = rate_limit.limiter.check_many([(key, lim)])
            if wait:
                logger.warning("rate limit: login bloqueado por %s", nome)
                return rate_limit.too_many(wait)

    user = login_user_db(email, password)

    if user is None:
        if use_limit:
            rate_limit.limiter.record_many([(ip_key, win), (pair_key, win), (acc_key, win)])
        return jsonify({"error": "Email ou senha inválidos"}), 401

    if use_limit:
        # sucesso zera só o par e-mail+IP
        rate_limit.limiter.reset(pair_key)

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
