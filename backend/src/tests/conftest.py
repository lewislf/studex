import os
from pathlib import Path

# Removido antes de importar o app, para a suíte não usar um Turso real; o modo
# turso é testado só com o driver falso (fake_libsql.py). CORS_ORIGINS e
# ADMIN_USER_IDS saem pelo mesmo motivo: os exportados para rodar o app local
# mudariam o padrão que os testes conferem.
for _var in ("TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN", "CORS_ORIGINS", "ADMIN_USER_IDS"):
    os.environ.pop(_var, None)

# auth.py exige JWT_SECRET
os.environ.setdefault("JWT_SECRET", "segredo-de-teste-" + "x" * 32)

import pytest

import auth

from auth import create_token
from database.database import init_db
from main import app


@pytest.fixture
def client(temp_db):
    db_path = temp_db

    app.config["TESTING"] = True
    app.config["DB_PATH"] = db_path
    # os testes de rate limit (test_user_security.py) ligam explicitamente
    app.config["RATELIMIT_ENABLED"] = False

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

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "real_user_check: usa a checagem real de existencia do usuario em auth"
    )


@pytest.fixture(autouse=True)
def _assume_user_exists(request, monkeypatch):
    """Tokens de teste não têm linha em users; _user_exists devolve True, salvo com real_user_check."""
    if request.node.get_closest_marker("real_user_check") is None:
        monkeypatch.setattr(auth, "_user_exists", lambda user_id: True)


@pytest.fixture(autouse=True)
def _isolar_banco_padrao(tmp_path, monkeypatch):
    """Roda cada teste numa pasta temporária, com o users.db padrão já inicializado."""
    pasta = tmp_path / "cwd"
    pasta.mkdir()
    monkeypatch.chdir(pasta)
    init_db(db_path=Path("users.db"))
