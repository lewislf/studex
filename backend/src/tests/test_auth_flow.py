"""
Teste de fluxo (persistência real via fixture temp_db):

    cadastro -> login -> matéria do usuário -> "envio de arquivo" -> salvo no db

Valida a jornada pedida de ponta a ponta. O passo de upload é representado
por `save_materials_db`, que é exatamente a persistência executada pela rota
`POST /users/<id>/documents` depois que o RAG/LLM geram os materiais. Não há
mock aqui: o banco é o SQLite temporário do fixture.
"""

from datetime import date

from database.database import (
    save_user_db,
    login_user_db,
    save_subject_db,
    save_materials_db,
    get_summaries_db,
    get_decks_db,
    get_flashcards_db,
    count_summaries_db,
    match_subject_user_db,
)


def test_signup_login_upload_persistence(temp_db):
    db_path, key_path = temp_db

    # 1. Cadastro de uma conta
    user_id = save_user_db(
        "Maria",
        "senha123",
        "maria@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id is not None

    # 2. Login com a conta recém-criada
    user = login_user_db(
        "maria@email.com",
        "senha123",
        db_path=db_path,
        key_path=key_path,
    )

    assert user is not None
    assert user.id == user_id
    assert user.email == "maria@email.com"

    # Senha errada e email inexistente não autenticam
    assert login_user_db("maria@email.com", "errada", db_path=db_path, key_path=key_path) is None
    assert login_user_db("ninguem@email.com", "senha123", db_path=db_path, key_path=key_path) is None

    # 3. Matéria do usuário: destino do upload
    subject_id = save_subject_db(
        user_id=user_id,
        name="Redes",
        desc="Redes de Computadores",
        domain=0,
        icon="book",
        color="#4361ee",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id is not None

    # 4. "Envio do arquivo": materiais gerados a partir do PDF são persistidos
    #    na matéria (mesmo passo que a rota de upload executa).
    materials = [
        {
            "tipo": "resumo",
            "titulo": "Camadas TCP/IP",
            "conteudo": {"texto": "Resumo das camadas."},
            "creation_date": date.today(),
        },
        {
            "tipo": "baralho",
            "titulo": "Revisão de Redes",
            "conteudo": {
                "flashcards": [
                    {"pergunta": "O que é TCP?", "resposta": "Protocolo confiável."},
                    {"pergunta": "O que é UDP?", "resposta": "Protocolo sem conexão."},
                ]
            },
            "creation_date": date.today(),
        },
    ]

    save_materials_db(subject_id, materials, db_path=db_path)

    # 5. Confere que ficou salvo no db, ligado à matéria do usuário cadastrado
    assert count_summaries_db(subject_id, db_path=db_path) == 1

    summaries = get_summaries_db(subject_id, db_path=db_path)
    assert summaries is not None and len(summaries) == 1
    assert summaries[0].titulo == "Camadas TCP/IP"

    decks = get_decks_db(subject_id, db_path=db_path)
    assert len(decks) == 1

    flashcards = get_flashcards_db(decks[0].id, db_path=db_path)
    assert len(flashcards) == 2

    # A matéria (e portanto os materiais salvos) pertence à conta cadastrada
    assert match_subject_user_db(subject_id, user_id, db_path=db_path) is True
