from datetime import date

from database.database import (
    save_user_db,
    save_subject_db,
    save_deck_db,
    get_deck_db,
    get_decks_db,
    delete_deck_db,
    count_deck_db,
)


def test_save_deck(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    subject_id = save_subject_db(
        user_id=user_id,
        name="Redes",
        desc="Redes de Computadores",
        domain="Computação",
        creation_date=date.today(),
        db_path=db_path,
    )

    deck_id = save_deck_db(
        subject_id=subject_id,
        titulo="TCP/IP",
        acuracia=90,
        novos=10,
        aprendendo=5,
        review=20,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert deck_id == 1

    deck = get_deck_db(deck_id, db_path=db_path)

    assert deck.titulo == "TCP/IP"
    assert deck.subject_id == subject_id
    assert deck.acuracia == 90
    assert deck.novos == 10
    assert deck.aprendendo == 5
    assert deck.review == 20


def test_delete_deck(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    subject_id = save_subject_db(
        user_id=user_id,
        name="IA",
        desc="Inteligência Artificial",
        domain="Computação",
        creation_date=date.today(),
        db_path=db_path,
    )

    deck_id = save_deck_db(
        subject_id=subject_id,
        titulo="ML",
        acuracia=80,
        novos=8,
        aprendendo=4,
        review=15,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert count_deck_db(subject_id, db_path) == 1

    deleted = delete_deck_db(deck_id, db_path)

    assert deleted is True
    assert count_deck_db(subject_id, db_path) == 0
    assert get_deck_db(deck_id, db_path=db_path) is None


def test_search_deck(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    subject_id = save_subject_db(
        user_id=user_id,
        name="POO",
        desc="Programação Orientada a Objetos",
        domain="Computação",
        creation_date=date.today(),
        db_path=db_path,
    )

    save_deck_db(
        subject_id=subject_id,
        titulo="Herança",
        acuracia=100,
        novos=2,
        aprendendo=1,
        review=30,
        creation_date=date.today(),
        db_path=db_path,
    )

    decks = get_decks_db(
        subject_id,
        db_path=db_path,
    )

    assert len(decks) == 1
    assert decks[0].titulo == "Herança"


def test_count_deck(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    subject_id = save_subject_db(
        user_id=user_id,
        name="Banco de Dados",
        desc="SQL",
        domain="Computação",
        creation_date=date.today(),
        db_path=db_path,
    )

    save_deck_db(
        subject_id,
        "SQL Básico",
        75,
        10,
        5,
        8,
        date.today(),
        db_path=db_path,
    )

    save_deck_db(
        subject_id,
        "Álgebra Relacional",
        90,
        3,
        2,
        12,
        date.today(),
        db_path=db_path,
    )

    assert count_deck_db(subject_id, db_path) == 2
