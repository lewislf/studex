from datetime import date
import sqlite3
import pytest

from database.database import (
    save_user_db,
    save_subject_db,
    get_subject_db,
    get_subjects_db,
    delete_subject_db,
    count_subjects_db,
)


def test_save_subject(temp_db):
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
        desc="Matéria de Redes",
        domain=55,
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id == 1

    subject = get_subject_db(
        subject_id,
        db_path=db_path,
    )

    assert subject != None

    assert subject.name == "Redes"
    assert subject.description == "Matéria de Redes"
    assert subject.domain == 55
    assert subject.user_id == user_id


def test_delete_subject(temp_db):
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
        creation_date=date.today(),
        db_path=db_path,
    )

    assert subject_id != None

    deleted = delete_subject_db(
        subject_id,
        db_path=db_path,
    )

    assert deleted is True
    assert get_subject_db(subject_id, db_path=db_path) is None


def test_search_subject(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id != None

    save_subject_db(
        user_id=user_id,
        name="Redes de Computadores",
        desc="Descrição",
        domain=55,
        creation_date=date.today(),
        db_path=db_path,
    )

    subjects = get_subjects_db(
        user_id,
        db_path=db_path,
    )

    assert subjects != None
    assert len(subjects) == 1
    assert subjects[0].name == "Redes de Computadores"

def test_subject_invalid_user(temp_db):
    db_path, key_path = temp_db

    with pytest.raises(sqlite3.IntegrityError):
        save_subject_db(
            user_id=999,
            name="Redes",
            desc="Descrição",
            domain=55,
            creation_date=date.today(),
            db_path=db_path,
        )

def test_count_subject(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert user_id != None

    save_subject_db(
        user_id=user_id,
        name="Redes de Computadores",
        desc="Descrição",
        domain=55,
        creation_date=date.today(),
        db_path=db_path,
    )

    subjects_cnt = count_subjects_db(
        user_id,
        db_path=db_path,
    )

    assert subjects_cnt == 1
