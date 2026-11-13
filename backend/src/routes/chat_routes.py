import logging
import sys
from datetime import date
from pathlib import Path

from flask import Blueprint, jsonify, request

import rate_limit
from auth import require_auth
from database.database import (
    match_subject_user_db,
    get_chats_db,
    get_chat_db,
    save_chat_db,
    delete_chat_db,
    save_chat_message_db,
    get_chat_messages_db,
    update_chat_title_db,
)

sys.path.append(str(Path(__file__).resolve().parent.parent / "rag_api"))
from chat import responder

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chats", __name__, url_prefix="/users/<int:user_id>/chats")

MAX_PERGUNTA = 1000


def _chat_do_usuario(chat_id: int, user_id: int):
    """O chat, se existir e for do usuário; None nos dois outros casos (mesmo 404, sem revelar qual)."""
    chat = get_chat_db(chat_id)
    if chat is None or chat.user_id != user_id:
        return None
    return chat


@chat_bp.get("")
@require_auth
def get_chats(user_id):
    """
    Lista os chats do usuário, do mais novo para o mais antigo.
    ---
    tags:
      - chats
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: Lista de chats (pode ser vazia), com nome e cor da matéria
    """
    return jsonify([c.to_dict() for c in get_chats_db(user_id)])


@chat_bp.get("/<int:chat_id>")
@require_auth
def get_chat(user_id, chat_id):
    """
    Busca um chat com o histórico de mensagens.
    ---
    tags:
      - chats
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: path
        name: chat_id
        type: integer
        required: true
    responses:
      200:
        description: Chat encontrado, com o campo mensagens
      404:
        description: Chat não encontrado
    """
    chat = _chat_do_usuario(chat_id, user_id)
    if chat is None:
        return jsonify({"error": "Chat não encontrado"}), 404

    response = chat.to_dict()
    response["mensagens"] = get_chat_messages_db(chat_id)
    return jsonify(response)


@chat_bp.post("")
@require_auth
def create_chat(user_id):
    """
    Cria um chat ligado a uma matéria do usuário.
    ---
    tags:
      - chats
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [subject_id]
          properties:
            subject_id: {type: integer, example: 2}
    responses:
      201:
        description: Chat criado
      400:
        description: subject_id ausente ou inválido
      404:
        description: Matéria não encontrada
    """
    body = request.get_json(silent=True) or {}
    subject_id = body.get("subject_id")

    # bool é subclasse de int: sem isso, true viraria a matéria 1
    if not isinstance(subject_id, int) or isinstance(subject_id, bool):
        return jsonify({"error": "subject_id deve ser um número inteiro"}), 400

    if not match_subject_user_db(subject_id, user_id):
        return jsonify({"error": "Matéria não encontrada"}), 404

    chat_id = save_chat_db(subject_id, user_id, "Novo chat", date.today())
    return jsonify(get_chat_db(chat_id).to_dict()), 201


@chat_bp.delete("/<int:chat_id>")
@require_auth
def delete_chat(user_id, chat_id):
    """
    Remove um chat e as mensagens dele.
    ---
    tags:
      - chats
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: path
        name: chat_id
        type: integer
        required: true
    responses:
      204:
        description: Chat removido
      404:
        description: Chat não encontrado
    """
    if _chat_do_usuario(chat_id, user_id) is None or not delete_chat_db(chat_id):
        return jsonify({"error": "Chat não encontrado"}), 404
    return "", 204


@chat_bp.post("/<int:chat_id>/messages")
@require_auth
def send_message(user_id, chat_id):
    """
    Envia uma pergunta ao chat e devolve a resposta baseada nos materiais da matéria.
    ---
    tags:
      - chats
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: path
        name: chat_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [question]
          properties:
            question: {type: string, example: "O que é k-coloração?"}
    responses:
      200:
        description: Resposta com answer e sources
      400:
        description: Pergunta ausente, vazia ou longa demais
      404:
        description: Chat não encontrado
      429:
        description: Muitas perguntas em pouco tempo
      503:
        description: Serviço de IA indisponível
    """
    body = request.get_json(silent=True) or {}
    question = body.get("question")

    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "Escreva uma pergunta"}), 400
    question = question.strip()
    if len(question) > MAX_PERGUNTA:
        return jsonify({"error": f"A pergunta pode ter no máximo {MAX_PERGUNTA} caracteres"}), 400

    chat = _chat_do_usuario(chat_id, user_id)
    if chat is None:
        return jsonify({"error": "Chat não encontrado"}), 404

    if rate_limit.enabled():
        # por usuário: cada pergunta gasta cota do Gemini
        cfg = rate_limit.limits()
        wait = rate_limit.limiter.check_and_record(
            rate_limit.mac_key("chat", str(user_id)),
            cfg["chat_user_max"], cfg["chat_window"],
        )
        if wait:
            logger.warning("rate limit: chat bloqueado por usuário")
            return rate_limit.too_many(wait)

    try:
        resultado = responder(question, user_id, chat.subject_id)
    except Exception:
        # LGPD: a pergunta não vai para o log
        logger.exception("Falha ao responder no chat %s", chat_id)
        return jsonify({"error": "O assistente está indisponível agora. Tente de novo em alguns minutos."}), 503

    # só salva depois da resposta, para não deixar pergunta sem resposta no histórico
    save_chat_message_db(chat_id, "user", question)
    save_chat_message_db(chat_id, "assistant", resultado["answer"], resultado["sources"])
    update_chat_title_db(chat_id, question[:50])

    return jsonify(resultado)
