"""
Testes da fila de estudo global (/users/:id/study): get_user_study_queue_db
(banco) e a rota do blueprint study_bp.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask import Flask

from database.database import (
    save_user_db,
    save_subject_db,
    save_deck_db,
    save_flashcard_db,
    get_user_study_queue_db,
    update_flashcard_review_db,
)
from enums.flashcard_status import FlashcardStatus
from routes.study_routes import study_bp

TODAY = date(2026, 7, 9)


def _local_app():
    app = Flask(__name__)
    app.register_blueprint(study_bp)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def study_client():
    with _local_app().test_client() as client:
        yield client


def _setup_two_decks(db_path):
    user_id = save_user_db("Felipe", "123456", "felipe@email.com", db_path=db_path)

    subject_a = save_subject_db(
        user_id, "Biologia", "desc", "geral", "icon", "#000", date.today().isoformat(), db_path=db_path
    )
    subject_b = save_subject_db(
        user_id, "Redes", "desc", "geral", "icon", "#000", date.today().isoformat(), db_path=db_path
    )

    deck_a = save_deck_db(subject_a, "Fotossíntese", 0, 0, 0, 0, date.today().isoformat(), db_path=db_path)
    deck_b = save_deck_db(subject_b, "TCP/IP", 0, 0, 0, 0, date.today().isoformat(), db_path=db_path)

    return user_id, subject_a, subject_b, deck_a, deck_b


# ---------------------------------------------------------------------------
# get_user_study_queue_db
# ---------------------------------------------------------------------------

def test_get_user_study_queue_cruza_baralhos_e_ordena_vencidos_primeiro(temp_db):
    db_path = temp_db
    user_id, subject_a, subject_b, deck_a, deck_b = _setup_two_decks(db_path)

    novo_id = save_flashcard_db(
        deck_a, "Pergunta nova", "Resposta nova", FlashcardStatus.NOVO.value, date.today(), db_path=db_path
    )
    vencido_id = save_flashcard_db(
        deck_b, "Pergunta vencida", "Resposta vencida", FlashcardStatus.REVIEW.value, date.today(), db_path=db_path
    )
    muito_vencido_id = save_flashcard_db(
        deck_a, "Pergunta bem vencida", "Resposta", FlashcardStatus.REVIEW.value, date.today(), db_path=db_path
    )

    update_flashcard_review_db(vencido_id, "review", "2026-07-08", 5, 2.5, 1, 0, db_path=db_path)
    update_flashcard_review_db(muito_vencido_id, "review", "2026-07-01", 5, 2.5, 1, 0, db_path=db_path)

    queue = get_user_study_queue_db(user_id, limit=20, today=TODAY, db_path=db_path)
    ids = [flashcard.id for flashcard, *_ in queue]

    assert ids == [muito_vencido_id, vencido_id, novo_id]

    # confere os campos extras de deck/matéria vindo do JOIN
    _, deck_id, deck_titulo, subject_id, subject_name = queue[0]
    assert deck_id == deck_a
    assert deck_titulo == "Fotossíntese"
    assert subject_id == subject_a
    assert subject_name == "Biologia"


def test_get_user_study_queue_respeita_limit(temp_db):
    db_path = temp_db
    user_id, subject_a, subject_b, deck_a, deck_b = _setup_two_decks(db_path)

    for i in range(5):
        save_flashcard_db(
            deck_a, f"Pergunta {i}", f"Resposta {i}", FlashcardStatus.NOVO.value, date.today(), db_path=db_path
        )

    queue = get_user_study_queue_db(user_id, limit=3, today=TODAY, db_path=db_path)
    assert len(queue) == 3


def test_get_user_study_queue_nao_traz_cards_de_outro_usuario(temp_db):
    db_path = temp_db
    user_id, subject_a, subject_b, deck_a, deck_b = _setup_two_decks(db_path)

    outro_user_id = save_user_db("Ana", "123456", "ana@email.com", db_path=db_path)
    outro_subject = save_subject_db(
        outro_user_id, "Química", "desc", "geral", "icon", "#000", date.today().isoformat(), db_path=db_path
    )
    outro_deck = save_deck_db(outro_subject, "Ligações", 0, 0, 0, 0, date.today().isoformat(), db_path=db_path)
    save_flashcard_db(
        outro_deck, "Pergunta", "Resposta", FlashcardStatus.NOVO.value, date.today(), db_path=db_path
    )

    queue = get_user_study_queue_db(user_id, limit=20, today=TODAY, db_path=db_path)
    assert queue == []


# ---------------------------------------------------------------------------
# Rota GET /users/:id/study
# ---------------------------------------------------------------------------

def fake_user():
    return SimpleNamespace(id=10, name="Felipe")


def fake_flashcard(**overrides):
    base = dict(
        id=5,
        deck_id=1,
        pergunta="Pergunta",
        resposta="Resposta",
        status="novo",
        due_date=None,
        interval_days=0,
        ease=2.5,
        reps=0,
        lapses=0,
    )
    base.update(overrides)
    card = SimpleNamespace(**base)
    card.to_dict = lambda: {
        "id": card.id,
        "deck_id": card.deck_id,
        "pergunta": card.pergunta,
        "resposta": card.resposta,
        "status": card.status,
        "due_date": card.due_date,
        "interval_days": card.interval_days,
        "ease": card.ease,
        "reps": card.reps,
        "lapses": card.lapses,
    }
    return card


def test_study_route_200_traz_campos_de_deck_e_materia(study_client, auth_headers):
    queue = [(fake_flashcard(), 1, "Fotossíntese", 2, "Biologia")]

    with patch("routes.study_routes.get_user_db", return_value=fake_user()), \
         patch("routes.study_routes.get_user_study_queue_db", return_value=queue):

        response = study_client.get("/users/10/study", headers=auth_headers(10))

    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 1
    card = body["cards"][0]
    assert card["deck_id"] == 1
    assert card["deck_titulo"] == "Fotossíntese"
    assert card["subject_id"] == 2
    assert card["subject_name"] == "Biologia"


def test_study_route_sem_cards_pendentes_e_200(study_client, auth_headers):
    with patch("routes.study_routes.get_user_db", return_value=fake_user()), \
         patch("routes.study_routes.get_user_study_queue_db", return_value=[]):

        response = study_client.get("/users/10/study", headers=auth_headers(10))

    assert response.status_code == 200
    body = response.get_json()
    assert body["cards"] == []
    assert body["total"] == 0


def test_study_route_respeita_limit_da_query(study_client, auth_headers):
    with patch("routes.study_routes.get_user_db", return_value=fake_user()), \
         patch("routes.study_routes.get_user_study_queue_db", return_value=[]) as mock_queue:

        study_client.get("/users/10/study?limit=5", headers=auth_headers(10))

    assert mock_queue.call_args.kwargs["limit"] == 5


def test_study_route_clamp_limit_maximo(study_client, auth_headers):
    with patch("routes.study_routes.get_user_db", return_value=fake_user()), \
         patch("routes.study_routes.get_user_study_queue_db", return_value=[]) as mock_queue:

        study_client.get("/users/10/study?limit=9999", headers=auth_headers(10))

    assert mock_queue.call_args.kwargs["limit"] == 200


def test_study_route_usuario_nao_encontrado_404(study_client, auth_headers):
    with patch("routes.study_routes.get_user_db", return_value=None):
        response = study_client.get("/users/999/study", headers=auth_headers(999))

    assert response.status_code == 404
