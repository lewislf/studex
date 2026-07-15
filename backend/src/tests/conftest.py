from pathlib import Path

import pytest

from auth import create_token
from database.database import init_db
from main import app


@pytest.fixture
def client(temp_db):
    db_path = temp_db

    app.config["TESTING"] = True
    app.config["DB_PATH"] = db_path

    with app.test_client() as client:
        yield client

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"

    init_db(db_path=db_path)

    return db_path

@pytest.fixture
def auth_headers():
    """Factory: auth_headers(user_id) → dict com Authorization header."""
    def _factory(user_id=1):
        token = create_token(user_id=user_id)
        return {"Authorization": f"Bearer {token}"}
    return _factory