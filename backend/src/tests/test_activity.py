"""
Testes de atividade diária (streak/heatmap): record_activity_db,
get_activity_days_db, compute_streak (função pura), a rota
GET /users/<id>/activity e o registro de atividade nas rotas de
revisão de flashcard e upload de documento.
"""

from datetime import date
from io import BytesIO
from unittest.mock import patch

from database.database import (
    save_user_db,
    record_activity_db,
    get_activity_days_db,
    compute_streak,
)


TODAY = date(2026, 7, 9)


### record_activity_db / get_activity_days_db ###

def test_record_activity_insere_e_incrementa(temp_db):
    db_path = temp_db
    user_id = save_user_db("Felipe", "123456", "felipe@email.com", db_path=db_path)

    record_activity_db(user_id, "2026-07-09", db_path=db_path)
    record_activity_db(user_id, "2026-07-09", db_path=db_path)
    record_activity_db(user_id, "2026-07-08", db_path=db_path)

    days = get_activity_days_db(user_id, "2026-01-01", db_path=db_path)

    assert days == {"2026-07-09": 2, "2026-07-08": 1}


def test_get_activity_days_respeita_since(temp_db):
    db_path = temp_db
    user_id = save_user_db("Felipe", "123456", "felipe@email.com", db_path=db_path)

    record_activity_db(user_id, "2026-01-01", db_path=db_path)
    record_activity_db(user_id, "2026-07-09", db_path=db_path)

    days = get_activity_days_db(user_id, "2026-07-01", db_path=db_path)

    assert days == {"2026-07-09": 1}


def test_record_activity_nao_levanta_excecao_com_db_invalido():
    # db_path apontando pra lugar inexistente: função nunca pode derrubar
    # a rota chamadora.
    record_activity_db(1, "2026-07-09", db_path="/caminho/que/nao/existe/db.sqlite")


### compute_streak ###

def test_compute_streak_hoje_ativo():
    days = {"2026-07-09", "2026-07-08", "2026-07-07"}
    assert compute_streak(days, TODAY) == 3


def test_compute_streak_so_ate_ontem():
    days = {"2026-07-08", "2026-07-07"}
    assert compute_streak(days, TODAY) == 2


def test_compute_streak_com_buraco():
    days = {"2026-07-09", "2026-07-08", "2026-07-06"}
    assert compute_streak(days, TODAY) == 2


def test_compute_streak_vazio():
    assert compute_streak(set(), TODAY) == 0


def test_compute_streak_apenas_hoje():
    days = {"2026-07-09"}
    assert compute_streak(days, TODAY) == 1


### GET /users/<id>/activity ###

def test_get_activity_route_200(client, auth_headers):
    fake_days = {"2026-07-08": 3, "2026-07-09": 1}

    with patch("routes.user_routes.get_user_db", return_value=object()), \
         patch("routes.user_routes.get_activity_days_db", return_value=fake_days), \
         patch("routes.user_routes.date") as mock_date:

        mock_date.today.return_value = TODAY

        response = client.get("/users/10/activity", headers=auth_headers(10))

    assert response.status_code == 200
    body = response.get_json()

    assert body == {
        "days": fake_days,
        "current_streak": 2,
        "today_active": True,
    }


def test_get_activity_route_user_not_found_404(client, auth_headers):
    with patch("routes.user_routes.get_user_db", return_value=None):
        response = client.get("/users/999/activity", headers=auth_headers(999))

    assert response.status_code == 404
    assert response.get_json() == {"error": "User not found"}


### Revisão de flashcard registra atividade ###

def test_review_flashcard_registra_atividade(client, auth_headers):
    from types import SimpleNamespace

    card = SimpleNamespace(
        id=5,
        deck_id=1,
        status="novo",
        interval_days=0,
        ease=2.5,
        reps=0,
        lapses=0,
        due_date=None,
        to_dict=lambda: {"id": 5, "status": "novo"},
    )
    deck = SimpleNamespace(id=1, subject_id=2, titulo="Baralho")

    with patch("routes.flashcard_routes.match_subject_user_db", return_value=True), \
         patch("routes.flashcard_routes.get_deck_db", return_value=deck), \
         patch("routes.flashcard_routes.get_flashcard_db", return_value=card), \
         patch("routes.flashcard_routes.update_flashcard_review_db"), \
         patch("routes.flashcard_routes.refresh_deck_counters_db"), \
         patch("routes.flashcard_routes.record_activity_db") as mock_activity:

        response = client.post(
            "/users/10/subjects/2/decks/1/flashcards/5/review",
            headers=auth_headers(10),
        json={"rating": "bom"},
        )

    assert response.status_code == 200
    mock_activity.assert_called_once_with(10, date.today().isoformat())


### Upload de documento registra atividade ###

def test_upload_registra_atividade(client, auth_headers, tmp_path):
    materials = [{"tipo": "resumo", "titulo": "T", "conteudo": {}, "creation_date": "2026-07-07"}]

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=materials), \
         patch("routes.document_routes.match_subject_user_db", return_value=True), \
         patch("routes.document_routes.save_materials_db"), \
         patch("routes.document_routes.record_activity_db") as mock_activity:

        response = client.post(
            "/users/10/documents",
            headers=auth_headers(10),
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
                "user_id": "10",
                "subject_id": "3",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 201
    mock_activity.assert_called_once_with(10, date.today().isoformat())


def test_upload_nao_registra_atividade_quando_validacao_falha(client, auth_headers, tmp_path):
    # user_id ausente: 400 antes de sequer salvar o arquivo, não deve
    # registrar atividade nenhuma.
    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.record_activity_db") as mock_activity:

        response = client.post(
            "/users/10/documents",
            headers=auth_headers(10),
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    mock_activity.assert_not_called()


def test_upload_nao_registra_atividade_quando_subject_de_outro_usuario(client, auth_headers, tmp_path):
    # subject_id não pertence ao usuário: 404 antes de salvar o arquivo.
    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents") as mock_load, \
         patch("routes.document_routes.match_subject_user_db", return_value=False), \
         patch("routes.document_routes.record_activity_db") as mock_activity:

        response = client.post(
            "/users/10/documents",
            headers=auth_headers(10),
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
                "user_id": "10",
                "subject_id": "3",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 404
    mock_load.assert_not_called()
    mock_activity.assert_not_called()
