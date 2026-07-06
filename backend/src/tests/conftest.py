from pathlib import Path

import pytest

from database.database import init_db
from main import app


@pytest.fixture
def client(temp_db):
    db_path, key_path = temp_db

    app.config["TESTING"] = True
    app.config["DB_PATH"] = db_path
    app.config["KEY_PATH"] = key_path

    with app.test_client() as client:
        yield client

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    key_path = tmp_path / "test.key"

    init_db(db_path=db_path, key_path=key_path)

    return db_path, key_path