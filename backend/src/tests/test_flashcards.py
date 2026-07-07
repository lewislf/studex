from datetime import date

from database.database import (
    save_user_db,
    save_subject_db,
    save_deck_db,
    save_flashcard_db,
    get_flashcard_db,
    get_flashcards_db,
    delete_flashcard_db,
    count_flashcards_db,
)

from enums.flashcard_status import FlashcardStatus


def test_save_flashcard(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id is not None

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

    assert subject_id is not None

    deck_id = save_deck_db(
        subject_id=subject_id,
        titulo="TCP/IP",
        acuracia=0,
        novos=1,
        aprendendo=0,
        review=0,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert deck_id is not None

    flashcard_id = save_flashcard_db(
        deck_id=deck_id,
        pergunta="O que é TCP?",
        resposta="Um protocolo de transporte.",
        status=FlashcardStatus.NOVO.value,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert flashcard_id == 1

    flashcard = get_flashcard_db(
        flashcard_id,
        db_path=db_path,
    )

    assert flashcard is not None
    assert flashcard.deck_id == deck_id
    assert flashcard.pergunta == "O que é TCP?"
    assert flashcard.resposta == "Um protocolo de transporte."
    assert flashcard.status == FlashcardStatus.NOVO.value


def test_delete_flashcard(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id is not None

    subject_id = save_subject_db(
        user_id=user_id,
        name="IA",
        desc="Inteligência Artificial",
        domain="Computação",
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id is not None

    deck_id = save_deck_db(
        subject_id=subject_id,
        titulo="Redes Neurais",
        acuracia=0,
        novos=1,
        aprendendo=0,
        review=0,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert deck_id is not None

    flashcard_id = save_flashcard_db(
        deck_id=deck_id,
        pergunta="O que é um neurônio?",
        resposta="Unidade básica de uma rede neural.",
        status=FlashcardStatus.NOVO.value,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert count_flashcards_db(deck_id, db_path) == 1

    deleted = delete_flashcard_db(
        flashcard_id,
        db_path,
    )

    assert deleted is True
    assert count_flashcards_db(deck_id, db_path) == 0
    assert get_flashcard_db(flashcard_id, db_path=db_path) is None


def test_search_flashcards(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id is not None

    subject_id = save_subject_db(
        user_id=user_id,
        name="POO",
        desc="Programação Orientada a Objetos",
        domain="Computação",
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id is not None

    deck_id = save_deck_db(
        subject_id=subject_id,
        titulo="Herança",
        acuracia=0,
        novos=2,
        aprendendo=0,
        review=0,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert deck_id is not None

    save_flashcard_db(
        deck_id,
        "O que é herança?",
        "Mecanismo de reutilização de código.",
        FlashcardStatus.NOVO.value,
        date.today(),
        db_path=db_path,
    )

    save_flashcard_db(
        deck_id,
        "O que é polimorfismo?",
        "Capacidade de assumir diferentes formas.",
        FlashcardStatus.NOVO.value,
        date.today(),
        db_path=db_path,
    )

    flashcards = get_flashcards_db(
        deck_id,
        db_path=db_path,
    )

    assert flashcards is not None
    assert len(flashcards) == 2


def test_count_flashcards(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id is not None

    subject_id = save_subject_db(
        user_id=user_id,
        name="Banco de Dados",
        desc="SQL",
        domain="Computação",
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id is not None

    deck_id = save_deck_db(
        subject_id=subject_id,
        titulo="SQL",
        acuracia=0,
        novos=2,
        aprendendo=0,
        review=0,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert deck_id is not None

    save_flashcard_db(
        deck_id,
        "O que é SELECT?",
        "Comando de consulta.",
        FlashcardStatus.NOVO.value,
        date.today(),
        db_path=db_path,
    )

    save_flashcard_db(
        deck_id,
        "O que é JOIN?",
        "Operação entre tabelas.",
        FlashcardStatus.NOVO.value,
        date.today(),
        db_path=db_path,
    )

    assert count_flashcards_db(deck_id, db_path) == 2
