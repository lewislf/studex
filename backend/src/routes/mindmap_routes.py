from flask import Blueprint, jsonify, request

from database.database import (
    get_subject_db,
    get_mindmap_db,
    get_mindmaps_db,
    save_mindmap_db,
    delete_mindmap_db,
    match_subject_user_db,
)

mindmap_bp = Blueprint("mindmaps", __name__, url_prefix="/users/<int:user_id>/subjects/<int:subject_id>/mindmaps")

@mindmap_bp.get("")
def get_mindmaps(user_id, subject_id):
    """
    Lista os Mapas mentais de um usuário.
    ---
    tags:
      - Mapa Mental
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
        description: Id da matéria ao qual o mapa mental pertence
    responses:
      200:
        description: Lista de Mapas mentais do usuário
      404:
        description: Nenhum mapa mental
    """
    mindmaps = get_mindmaps_db(subject_id)
    
    if mindmaps is None:
        return jsonify({"error": "mindmaps not found"}), 404
    
    subject = get_subject_db(subject_id)
    
    if subject is None:
        return jsonify({"error": "No subject has been found for this mindmap"}), 404
    
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    response = []
    for m in mindmaps:
        mindmap = m.to_dict()
        response.append(mindmap)
           
    return jsonify(response)
        


@mindmap_bp.get("/<int:mindmap_id>")
def get_mindmap(user_id, subject_id, mindmap_id):
    """
    Busca o Mapa mental de um usuário.
    ---
    tags:
      - Mapa Mental
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
        description: Id da matéria ao qual o mapa mental pertence
      - in: path
        name: mindmap_id
        type: integer
        required: true
        description: Id da matéria ao qual o mapa mental pertence
    responses:
      200:
        description: Mapa mental do usuário
      404:
        description: Nenhum mapa mental
    """
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404

    mindmap = get_mindmap_db(mindmap_id)
    
    if mindmap is None:
        return jsonify({"error": "mindmap not found"}), 404

    if subject_id != mindmap.subject_id:
        return jsonify({"error": "mindmap with id " + str(mindmap_id) + "is not from this subject"}), 404
 
    subject = get_subject_db(mindmap.subject_id)

    if subject is None:
        return jsonify({"error": "mindmap has not been found"}), 404

    return jsonify(mindmap.to_dict())



@mindmap_bp.post("")
def create_mindmap(user_id, subject_id):
    """
    Cria um novo mapa mental para um usuário.
    ---
    tags:
    - Mapa Mental
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
            tipo:
            type: string
            example: "mapa_mental"

            titulo:
            type: string
            example: "Planolândia — Mapa Mental de Estudo"

            creation_date:
            type: string
            example: "2026-07-04"

            conteudo:
            type: object
            properties:

                nodes:
                type: array
                items:
                    type: object
                    properties:
                    id:
                        type: string
                        example: "1"

                    type:
                        type: string
                        example: "tema_central"

                    data:
                        type: object
                        properties:
                        label:
                            type: string
                            example: "Planolândia"

                        conteudo:
                            type: string
                            example: "Narrativa satírica ambientada num mundo bidimensional."

                edges:
                type: array
                items:
                    type: object
                    properties:
                    id:
                        type: string
                        example: "e1-2"

                    source:
                        type: string
                        example: "1"

                    target:
                        type: string
                        example: "2"

    responses:
    201:
        description: Mapa mental criado (retorna o id)
    """
    body = request.get_json()

    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    mindmap_id = save_mindmap_db(
                        subject_id=subject_id,
                        titulo=material["titulo"],
                        conteudo=json.dumps(material["conteudo"], ensure_ascii=False),
                        creation_date=material["creation_date"],
                    )

    return jsonify({"id": mindmap_id}), 201


@mindmap_bp.delete("/<int:mindmap_id>")
def delete_mindmap(user_id, subject_id, mindmap_id):
    """
    Remove um Mapa mental pelo id.
    ---
    tags:
      - Mapa mental
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
        name: mindmap_id
        type: integer
        required: true
    responses:
      204:
        description: Mapa mental removido
      404:
        description: Mapa mental não encontrado
    """
    has_subj = match_subject_user_db(subject_id, user_id)

    if has_subj is False:
        return jsonify({"error": "User does not have this subject!"}), 404
    
    mindmap = get_mindmap_db(mindmap_id)

    if mindmap is not None and subject_id != mindmap.subject_id:
        return jsonify({"error": "mindmap with id " + mindmap_id + "is not from this subject"}), 404

    if delete_mindmap_db(mindmap_id):
        return "", 204

    return jsonify({"error": "mindmap not found"}), 404