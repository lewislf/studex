from pathlib import Path

import pytest

from database.database import init_db


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    key_path = tmp_path / "test.key"

    init_db(db_path=db_path, key_path=key_path)

    return db_path, key_path