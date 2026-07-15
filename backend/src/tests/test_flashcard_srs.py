"""
Testes de repetição espaçada (SRS): srs.apply_review (função pura),
funções de banco (get_study_queue_db, refresh_deck_counters_db) e as
rotas /study e /review.
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from srs import apply_review

from database.database import (
    save_user_db,
    save_subject_db,
    save_deck_db,
    save_flashcard_db,
    get_flashcard_db,
    get_deck_db,
    get_study_queue_db,
    update_flashcard_review_db,
    refresh_deck_counters_db,
)
from enums.flashcard_status import FlashcardStatus


TODAY = date(2026, 7, 9)


def make_card(status="novo", interval_days=0, ease=2.5, reps=0, lapses=0):
    return SimpleNamespace(
        status=status,
        interval_days=interval_days,
        ease=ease,
        reps=reps,
        lapses=lapses,
    )


# ---------------------------------------------------------------------------
# apply_review
# ---------------------------------------------------------------------------

def test_apply_review_reset_card_novo():
    card = make_card(status="novo")
    status, due_date, interval, ease, reps, lapses = apply_review(card, "reset", today=TODAY)

    assert status == "reaprendendo"
    assert interval == 0
    assert due_date == TODAY.isoformat()
    assert ease == pytest.approx(2.3)
    assert lapses == 1
    assert reps == 0  # reset não soma reps


def test_apply_review_reset_ease_tem_piso():
    card = make_card(status="review", ease=1.35)
    _, _, _, ease, _, _ = apply_review(card, "reset", today=TODAY)
    assert ease == pytest.approx(1.3)


def test_apply_review_dificil_card_novo_repete_na_sessao():
    card = make_card(status="novo")
    status, due_date, interval, ease, reps, lapses = apply_review(card, "dificil", today=TODAY)

    assert status == "aprendendo"
    assert interval == 0
    assert due_date == TODAY.isoformat()
    assert reps == 1


def test_apply_review_dificil_card_review_cresce_pouco():
    card = make_card(status="review", interval_days=10, ease=2.5)
    status, due_date, interval, ease, reps, lapses = apply_review(card, "dificil", today=TODAY)

    assert status == "review"
    assert interval == pytest.approx(12.0)
    assert ease == pytest.approx(2.35)
    assert due_date == (TODAY + timedelta(days=12)).isoformat()
    assert reps == 1


def test_apply_review_bom_card_novo_gradua_review():
    card = make_card(status="novo")
    status, due_date, interval, ease, reps, lapses = apply_review(card, "bom", today=TODAY)

    assert status == "review"
    assert interval == 1
    assert due_date == (TODAY + timedelta(days=1)).isoformat()
    assert reps == 1


def test_apply_review_bom_card_review_cresce_pela_ease():
    card = make_card(status="review", interval_days=10, ease=2.0)
    status, due_date, interval, ease, reps, lapses = apply_review(card, "bom", today=TODAY)

    assert status == "review"
    assert interval == pytest.approx(20.0)
    assert due_date == (TODAY + timedelta(days=20)).isoformat()


def test_apply_review_facil_card_novo_gradua_com_intervalo_maior():
    card = make_card(status="novo", ease=2.5)
    status, due_date, interval, ease, reps, lapses = apply_review(card, "facil", today=TODAY)

    assert status == "review"
    assert interval == 4
    assert ease == pytest.approx(2.65)
    assert due_date == (TODAY + timedelta(days=4)).isoformat()


def test_apply_review_facil_card_review_cresce_agressivo():
    card = make_card(status="review", interval_days=10, ease=2.0)
    status, due_date, interval, ease, reps, lapses = apply_review(card, "facil", today=TODAY)

    assert status == "review"
    assert interval == pytest.approx(10 * 2.0 * 1.3)
    assert ease == pytest.approx(2.15)


def test_apply_review_rating_invalido_levanta_value_error():
    card = make_card()
    with pytest.raises(ValueError):
        apply_review(card, "otimo", today=TODAY)


# ---------------------------------------------------------------------------
# Fixture auxiliar: cria user/subject/deck pra testes de banco
# ---------------------------------------------------------------------------

def _setup_deck(db_path):
    user_id = save_user_db("Felipe", "123456", "felipe@email.com", db_path=db_path)
    subject_id = save_subject_db(
        user_id=user_id,
        name="Redes",
        desc="Redes de Computadores",
        domain="Computação",
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )
    deck_id = save_deck_db(
        subject_id=subject_id,
        titulo="TCP/IP",
        acuracia=0,
        novos=0,
        aprendendo=0,
        review=0,
        creation_date=date.today(),
        db_path=db_path,
    )
    return user_id, subject_id, deck_id


# ---------------------------------------------------------------------------
# get_study_queue_db
# ---------------------------------------------------------------------------

def test_get_study_queue_vencidos_antes_de_novos(temp_db):
    db_path = temp_db
    _, _, deck_id = _setup_deck(db_path)

    novo_id = save_flashcard_db(
        deck_id, "Pergunta nova", "Resposta nova", FlashcardStatus.NOVO.value, date.today(), db_path=db_path
    )
    vencido_id = save_flashcard_db(
        deck_id, "Pergunta vencida", "Resposta vencida", FlashcardStatus.REVIEW.value, date.today(), db_path=db_path
    )
    # vencido há mais tempo que outro vencido
    muito_vencido_id = save_flashcard_db(
        deck_id, "Pergunta bem vencida", "Resposta", FlashcardStatus.REVIEW.value, date.today(), db_path=db_path
    )

    update_flashcard_review_db(vencido_id, "review", "2026-07-08", 5, 2.5, 1, 0, db_path=db_path)
    update_flashcard_review_db(muito_vencido_id, "review", "2026-07-01", 5, 2.5, 1, 0, db_path=db_path)

    queue = get_study_queue_db(deck_id, limit=20, today=TODAY, db_path=db_path)

    ids = [c.id for c in queue]
    # os dois vencidos vêm antes do novo, e o mais atrasado (07-01) vem primeiro
    assert ids.index(muito_vencido_id) < ids.index(vencido_id) < ids.index(novo_id)


def test_get_study_queue_respeita_limit(temp_db):
    db_path = temp_db
    _, _, deck_id = _setup_deck(db_path)

    for i in range(5):
        save_flashcard_db(
            deck_id, f"Pergunta {i}", f"Resposta {i}", FlashcardStatus.NOVO.value, date.today(), db_path=db_path
        )

    queue = get_study_queue_db(deck_id, limit=3, today=TODAY, db_path=db_path)
    assert len(queue) == 3


def test_get_study_queue_deck_sem_cards_retorna_vazio(temp_db):
    db_path = temp_db
    _, _, deck_id = _setup_deck(db_path)

    queue = get_study_queue_db(deck_id, limit=20, today=TODAY, db_path=db_path)
    assert queue == []


# ---------------------------------------------------------------------------
# refresh_deck_counters_db
# ---------------------------------------------------------------------------

def test_refresh_deck_counters_conta_reaprendendo_como_aprendendo(temp_db):
    db_path = temp_db
    _, _, deck_id = _setup_deck(db_path)

    save_flashcard_db(deck_id, "Q1", "R1", FlashcardStatus.NOVO.value, date.today(), db_path=db_path)
    id_aprendendo = save_flashcard_db(deck_id, "Q2", "R2", FlashcardStatus.APRENDENDO.value, date.today(), db_path=db_path)
    id_reaprendendo = save_flashcard_db(deck_id, "Q3", "R3", FlashcardStatus.NOVO.value, date.today(), db_path=db_path)
    id_review = save_flashcard_db(deck_id, "Q4", "R4", FlashcardStatus.NOVO.value, date.today(), db_path=db_path)

    update_flashcard_review_db(id_reaprendendo, "reaprendendo", "2026-07-09", 0, 2.3, 0, 1, db_path=db_path)
    update_flashcard_review_db(id_review, "review", "2026-07-10", 1, 2.5, 1, 0, db_path=db_path)

    refresh_deck_counters_db(deck_id, db_path=db_path)

    deck = get_deck_db(deck_id, db_path=db_path)
    assert deck.novos == 1
    assert deck.aprendendo == 2  # aprendendo + reaprendendo
    assert deck.review == 1


# ---------------------------------------------------------------------------
# Rotas /study e /review
# ---------------------------------------------------------------------------

def fake_deck(subject_id=2):
    return SimpleNamespace(id=1, subject_id=subject_id, titulo="TCP/IP")


def fake_subject():
    return SimpleNamespace(id=2, name="Redes")


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


def test_study_route_200(client, auth_headers):
    with patch("routes.deck_routes.match_subject_user_db", return_value=True), \
         patch("routes.deck_routes.get_deck_db", return_value=fake_deck()), \
         patch("routes.deck_routes.get_subject_db", return_value=fake_subject()), \
         patch("routes.deck_routes.get_study_queue_db", return_value=[fake_flashcard()]):

        response = client.get("/users/10/subjects/2/decks/1/study", headers=auth_headers(10))

    assert response.status_code == 200
    body = response.get_json()
    assert body["deck"] == {"id": 1, "titulo": "TCP/IP", "subject_id": 2, "subject_name": "Redes"}
    assert body["total"] == 1
    assert len(body["cards"]) == 1


def test_study_route_deck_sem_cards_ainda_e_200(client, auth_headers):
    with patch("routes.deck_routes.match_subject_user_db", return_value=True), \
         patch("routes.deck_routes.get_deck_db", return_value=fake_deck()), \
         patch("routes.deck_routes.get_subject_db", return_value=fake_subject()), \
         patch("routes.deck_routes.get_study_queue_db", return_value=[]):

        response = client.get("/users/10/subjects/2/decks/1/study", headers=auth_headers(10))

    assert response.status_code == 200
    body = response.get_json()
    assert body["cards"] == []
    assert body["total"] == 0


def test_study_route_deck_not_found_404(client, auth_headers):
    with patch("routes.deck_routes.match_subject_user_db", return_value=True), \
         patch("routes.deck_routes.get_deck_db", return_value=None):

        response = client.get("/users/10/subjects/2/decks/999/study", headers=auth_headers(10))

    assert response.status_code == 404


def test_review_route_rating_invalido_400(client, auth_headers):
    with patch("routes.flashcard_routes.match_subject_user_db", return_value=True), \
         patch("routes.flashcard_routes.get_deck_db", return_value=fake_deck()), \
         patch("routes.flashcard_routes.get_flashcard_db", return_value=fake_flashcard()):

        response = client.post(
            "/users/10/subjects/2/decks/1/flashcards/5/review",
            headers=auth_headers(10),
        json={"rating": "excelente"},
        )

    assert response.status_code == 400


def test_review_route_fluxo_feliz_200(client, auth_headers):
    card = fake_flashcard(status="novo")

    with patch("routes.flashcard_routes.match_subject_user_db", return_value=True), \
         patch("routes.flashcard_routes.get_deck_db", return_value=fake_deck()), \
         patch("routes.flashcard_routes.get_flashcard_db", return_value=card), \
         patch("routes.flashcard_routes.update_flashcard_review_db") as mock_update, \
         patch("routes.flashcard_routes.refresh_deck_counters_db") as mock_refresh:

        response = client.post(
            "/users/10/subjects/2/decks/1/flashcards/5/review",
            headers=auth_headers(10),
        json={"rating": "bom"},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "review"
    assert body["interval_days"] == 1
    mock_update.assert_called_once()
    mock_refresh.assert_called_once_with(1)


def test_review_route_flashcard_not_found_404(client, auth_headers):
    with patch("routes.flashcard_routes.match_subject_user_db", return_value=True), \
         patch("routes.flashcard_routes.get_deck_db", return_value=fake_deck()), \
         patch("routes.flashcard_routes.get_flashcard_db", return_value=None):

        response = client.post(
            "/users/10/subjects/2/decks/1/flashcards/999/review",
            headers=auth_headers(10),
        json={"rating": "bom"},
        )

    assert response.status_code == 404
