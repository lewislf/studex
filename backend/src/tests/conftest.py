import os
from pathlib import Path

# Os testes NUNCA devem falar com um Turso real: se o terminal tiver
# TURSO_DATABASE_URL/TURSO_AUTH_TOKEN exportados (ex.: depois de rodar o
# scripts/turso_smoke.py), o backend escolheria "turso" na importação e a
# suíte inteira iria para a rede (lenta e escrevendo no banco remoto).
# Removemos ANTES de importar o app; o modo turso é testado só com o
# driver falso (tests/fake_libsql.py), que liga as variáveis por conta própria.
for _var in ("TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"):
    os.environ.pop(_var, None)

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
    # Rate limit desligado por padrão nos testes; os testes de rate limit (test_user_security.py) ligam explicitamente.
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
    """Os testes de rota criam tokens sem linha em users; por padrao a checagem
    de existencia do usuario (auth._user_exists) devolve True. Use
    @pytest.mark.real_user_check para exercitar a checagem real."""
    if request.node.get_closest_marker("real_user_check") is None:
        monkeypatch.setattr(auth, "_user_exists", lambda user_id: True)


@pytest.fixture(autouse=True)
def _isolar_banco_padrao(tmp_path, monkeypatch):
    """Cada teste roda numa pasta temporária própria. O banco padrão
    (DB_PATH = "users.db", relativo à pasta atual) passa a ser um arquivo
    descartável dessa pasta, já com as tabelas — então nenhum teste cria ou
    altera o users.db da pasta do projeto, mesmo quando uma rota chama uma
    função de banco que o teste não substituiu (ex.: record_activity_db)."""
    pasta = tmp_path / "cwd"
    pasta.mkdir()
    monkeypatch.chdir(pasta)
    init_db(db_path=Path("users.db"))
