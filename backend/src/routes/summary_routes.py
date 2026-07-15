from flask import Blueprint, jsonify, request
import json

from auth import require_auth
from database.database import (
    get_subject_db,
    get_summary_db,
    get_summaries_db,
    save_summary_db,
    delete_summary_db,
    match_subject_user_db,
)

summary_bp = Blueprint("summaries", __name__, url_prefix="/users/<int:user_id>/subjects/<int:subject_id>/summaries")


@summary_bp.get("")
@require_auth
def get_summaries(user_id, subject_id):
    """
    Lista os resumos de um usuário.
    ---
    tags:
      - Resumos
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: Id do usuário dono das matérias
      - in: path
        name: subject_id
        type: integer
        required: true
        description: Id da matéria ao qual o resumo pertence
    responses:
      200:
        description: Lista de resumos do usuário
      404:
        description: Nenhum resumo
    """
    summaries = get_summaries_db(subject_id)
    
    if summaries is None:
        return jsonify({"error": "summaries not found"}), 404
    
    subject = get_subject_db(subject_id)
    
    if subject is None:
        return jsonify({"error": "No subject has been found for this summary"}), 404
    
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    response = []
    for s in summaries:
        summary = s.to_dict()
        summary["conteudo"] = json.loads(summary["conteudo"])
        response.append(summary)
           
    return jsonify(response)
        


@summary_bp.get("/<int:summary_id>")
@require_auth
def get_summary(user_id, subject_id, summary_id):
    """
    Busca um resumo pelo id.
    ---
    tags:
      - Resumos
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: path
        name: subject_id
        type: integer
        required: true
      - in: path
        name: summary_id
        type: integer
        required: true
    responses:
      200:
        description: Resumo encontrado
      404:
        description: Resumo não encontrado
    """
    summary = get_summary_db(summary_id)
    
    if summary is None:
        return jsonify({"error": "summary not found"}), 404

    if subject_id != summary.subject_id:
        return jsonify({"error": "summary with id " + str(summary_id) + "is not from this subject"}), 404
 
    subject = get_subject_db(summary.subject_id)

    if subject is None:
        return jsonify({"error": "summary has not been found"}), 404
    
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    response = summary.to_dict()
    response["conteudo"] = json.loads(response["conteudo"])

    return jsonify(response)



@summary_bp.post("")
@require_auth
def create_summary(user_id, subject_id):
    """
    Cria um novo resumo para um usuário.
    ---
    tags:
      - Resumos
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: path
        name: subject_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [tipo, titulo, creation_date, conteudo]
          properties:
            tipo: {type: string, example: "resumo"}
            titulo: {type: string, example: "Planolândia"}
            creation_date: {type: string, example: "2026-07-04"}
            conteudo:
                type: object
                properties:
                    texto: {type: string, example: "Planolândia (Flatland), de Edwin A. Abbott..."}

                    topicos_chave:
                        type: array
                        items:
                            type: string

                        example:
                            - "Estrutura social hierárquica baseada em número de lados"

                            - "Papel das mulheres como linhas retas sem direitos"

                            - "Visita da Esfera e revelação da terceira dimensão"
    responses:
      201:
        description: Resumo criado (retorna o id)
    """
    body = request.get_json()

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    conteudo_json_in_str = json.dumps(body["conteudo"], ensure_ascii=False)

    summary_id = save_summary_db(
        subject_id,
        body["titulo"],
        conteudo_json_in_str,
        body["creation_date"],
    )

    return jsonify({"id": summary_id}), 201


@summary_bp.delete("/<int:summary_id>")
@require_auth
def delete_summary(user_id, subject_id, summary_id):
    """
    Remove um resumo pelo id.
    ---
    tags:
      - Resumos
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: path
        name: subject_id
        type: integer
        required: true
      - in: path
        name: summary_id
        type: integer
        required: true
    responses:
      204:
        description: Resumo removido
      404:
        description: Resumo não encontrado
    """
    summary = get_summary_db(summary_id)

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    if summary is not None and subject_id != summary.subject_id:
        return jsonify({"error": "summary with id " + str(summary_id) + " is not from this subject"}), 404

    if delete_summary_db(summary_id):
        return "", 204

    return jsonify({"error": "summary not found"}), 404
