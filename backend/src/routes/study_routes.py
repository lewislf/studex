from datetime import date

from flask import Blueprint, jsonify, request

from auth import require_auth
from database.database import get_user_db, get_user_study_queue_db

study_bp = Blueprint("study", __name__, url_prefix="/users/<int:user_id>/study")


@study_bp.get("")
@require_auth
def get_global_study_queue(user_id):
    """
    Monta a fila de estudo (SRS) global de um usuário: cards de todos os
    baralhos de todas as matérias, vencidos primeiro (mais atrasados
    antes), depois cards novos, até o limite pedido.
    ---
    tags:
      - Revisões
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: ID do usuário
      - in: query
        name: limit
        type: integer
        required: false
        description: Número máximo de cards na fila (default 20, 1..200)
    responses:
      200:
        description: Fila de estudo global montada (cards pode vir vazio)
        schema:
          type: object
          properties:
            cards:
              type: array
              items:
                type: object
                properties:
                  id: {type: integer}
                  pergunta: {type: string}
                  resposta: {type: string}
                  status: {type: string}
                  due_date: {type: string}
                  interval_days: {type: number}
                  ease: {type: number}
                  reps: {type: integer}
                  lapses: {type: integer}
                  deck_id: {type: integer}
                  deck_titulo: {type: string}
                  subject_id: {type: integer}
                  subject_name: {type: string}
            total: {type: integer}
      404:
        description: Usuário não encontrado
    """
    user = get_user_db(user_id)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20

    limit = max(1, min(200, limit))

    queue = get_user_study_queue_db(user_id, limit=limit, today=date.today())

    cards = []
    for flashcard, deck_id, deck_titulo, subject_id, subject_name in queue:
        card = flashcard.to_dict() | {
            "deck_id": deck_id,
            "deck_titulo": deck_titulo,
            "subject_id": subject_id,
            "subject_name": subject_name,
        }
        cards.append(card)

    return jsonify({"cards": cards, "total": len(cards)})
