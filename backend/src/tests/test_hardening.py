"""CORS restrito, JWT_SECRET obrigatório e 404 para deck de outra matéria."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

SRC = Path(__file__).resolve().parent.parent


def _importar_auth(env_extra):
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET"}
    env.update(env_extra)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SRC), env.get("PYTHONPATH", "")]))
    return subprocess.run([sys.executable, "-c", "import auth"], cwd=SRC, env=env,
                          capture_output=True, text=True)


def test_sem_jwt_secret_o_app_nao_sobe():
    r = _importar_auth({})
    assert r.returncode != 0
    assert "JWT_SECRET não definido" in r.stderr


def test_jwt_secret_vazio_tambem_bloqueia():
    r = _importar_auth({"JWT_SECRET": "   "})
    assert r.returncode != 0


def test_com_jwt_secret_sobe():
    r = _importar_auth({"JWT_SECRET": "a" * 40})
    assert r.returncode == 0, r.stderr


def test_cors_origens_padrao():
    import main
    assert "https://studex-dusky.vercel.app" in main.CORS_ORIGINS
    assert "*" not in main.CORS_ORIGINS


def _cors_real():
    import flask_cors
    return hasattr(flask_cors, "cross_origin")  # o stub de teste não tem


@pytest.mark.skipif(not _cors_real(), reason="flask-cors real não instalado neste ambiente")
def test_cors_aceita_frontend_e_recusa_outros(client):
    ok = client.get("/routes", headers={"Origin": "https://studex-dusky.vercel.app"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "https://studex-dusky.vercel.app"
    ruim = client.get("/routes", headers={"Origin": "https://site-malicioso.example"})
    assert "Access-Control-Allow-Origin" not in ruim.headers


def test_deck_de_outra_materia_da_404_e_nao_500(client, auth_headers):
    deck = SimpleNamespace(id=7, subject_id=99)
    with patch("routes.deck_routes.get_deck_db", return_value=deck), \
         patch("routes.deck_routes.match_subject_user_db", return_value=True):
        r1 = client.get("/users/10/subjects/3/decks/7", headers=auth_headers(10))
        r2 = client.delete("/users/10/subjects/3/decks/7", headers=auth_headers(10))
    for r in (r1, r2):
        assert r.status_code == 404
        assert r.get_json()["error"] == "deck with id 7 is not from this subject"
