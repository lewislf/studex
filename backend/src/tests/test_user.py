from database.database import (
    save_user_db,
    get_user_db,
    get_users_db,
    delete_user_db,
    count_people_db,
)


def test_save_user(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Felipe",
        "123456",
        "felipe@email.com",
        db_path=db_path,
        key_path=key_path
    )

    assert user_id == 1

    user = get_user_db(
        user_id,
        db_path=db_path,
    )

    assert user.name == "Felipe"
    assert user.email == "felipe@email.com"

def test_delete_user(temp_db):
    db_path, key_path = temp_db

    user_id = save_user_db(
        "Ana",
        "123",
        "ana@email.com",
        db_path=db_path,
        key_path=key_path,
    )

    assert count_people_db(db_path) == 1

    deleted = delete_user_db(user_id, db_path)

    assert deleted is True
    assert count_people_db(db_path) == 0

def test_search_user(temp_db):
    db_path, key_path = temp_db

    save_user_db(
        "Felipe",
        "123",
        "f@email.com",
        db_path=db_path,
        key_path=key_path
    )

    users = get_users_db(
        "Fel",
        db_path=db_path,
    )

    assert len(users) == 1
    assert users[0].name == "Felipe"