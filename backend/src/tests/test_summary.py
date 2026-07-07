from datetime import date
from re import sub

from database.database import (
    save_user_db,
    save_subject_db,
    save_summary_db,
    get_summary_db,
    get_summaries_db,
    delete_summary_db,
    count_summaries_db
)


def test_save_summary(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id != None

    subject_id = save_subject_db(
        user_id=user_id,
        name="Redes",
        desc="Redes de Computadores",
        domain=55,
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id != None

    summary_id = save_summary_db(
        subject_id=subject_id,
        titulo="Modelo TCP/IP",
        conteudo="Resumo sobre as camadas do TCP/IP.",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert summary_id == 1

    summary = get_summary_db(
        summary_id,
        db_path=db_path,
    )

    assert summary.titulo == "Modelo TCP/IP"
    assert summary.conteudo == "Resumo sobre as camadas do TCP/IP."
    assert summary.subject_id == subject_id


def test_delete_summary(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id != None

    subject_id = save_subject_db(
        user_id=user_id,
        name="IA",
        desc="Inteligência Artificial",
        domain=55,
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id != None

    summary_id = save_summary_db(
        subject_id=subject_id,
        titulo="Redes Neurais",
        conteudo="Perceptrons multicamadas.",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert summary_id != None

    deleted = delete_summary_db(
        summary_id,
        db_path=db_path,
    )

    assert deleted is True
    assert get_summary_db(summary_id, db_path=db_path) is None


def test_search_summary(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id != None

    subject_id = save_subject_db(
        user_id=user_id,
        name="POO",
        desc="Programação Orientada a Objetos",
        domain=55,
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id != None

    save_summary_db(
        subject_id=subject_id,
        titulo="Herança",
        conteudo="Classes derivadas.",
        creation_date=date.today(),
        db_path=db_path,
    )

    summaries = get_summaries_db(
        "Her",
        db_path=db_path,
    )

    assert summaries != None
    assert len(summaries) == 1
    assert summaries[0].titulo == "Herança"

def test_count_summary(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id != None

    subject_id = save_subject_db(
        user_id=user_id,
        name="POO",
        desc="Programação Orientada a Objetos",
        domain=55,
        icon="globe",
        color="#e63946",
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id != None

    save_summary_db(
        subject_id=subject_id,
        titulo="Herança",
        conteudo="Classes derivadas.",
        creation_date=date.today(),
        db_path=db_path,
    )

    summaries_count = count_summaries_db(
        subject_id,
        db_path=db_path,
    )

    assert summaries_count == 1
