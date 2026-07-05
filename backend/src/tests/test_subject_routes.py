"""
Testes unitários das rotas de matéria (subject).

As funções de banco (`*_db`) são substituídas por mocks — nenhum teste toca
banco real ou rede. O test_client do Flask roda in-process.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask import Flask

from routes.subject_routes import subject_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(subject_bp)
    return app.test_client()


def _fake_subject(**kwargs):
    base = dict(id=1, name="Redes", user_id=1, description="Redes de Computadores",
                date="2026-07-05", domain=55)
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_list_subjects_success(client):
    fakes = [_fake_subject(id=1, name="Redes"), _fake_subject(id=2, name="POO")]

    with patch("routes.subject_routes.get_subjects_by_user_db", return_value=fakes) as mock_get:
        resp = client.get("/subjects?user_id=1")

    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 2
    assert body[0]["id"] == 1
    assert body[0]["title"] == "Redes"
    assert body[1]["title"] == "POO"
    mock_get.assert_called_once_with("1")


def test_list_subjects_empty(client):
    with patch("routes.subject_routes.get_subjects_by_user_db", return_value=[]):
        resp = client.get("/subjects?user_id=99")

    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_subjects_missing_user_id(client):
    resp = client.get("/subjects")

    assert resp.status_code == 400
    assert "user_id" in resp.get_json()["error"]


def test_create_subject(client):
    payload = {
        "user_id": 1, "name": "Redes", "description": "desc",
        "domain": 55, "date": "2026-07-05",
    }

    with patch("routes.subject_routes.save_subject_db", return_value=7) as mock_save:
        resp = client.post("/subjects", json=payload)

    assert resp.status_code == 201
    assert resp.get_json() == {"id": 7}
    mock_save.assert_called_once_with(1, "Redes", "desc", 55, "2026-07-05")


def test_get_subject_not_found(client):
    with patch("routes.subject_routes.get_subject_db", return_value=None):
        resp = client.get("/subjects/123")

    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_delete_subject_success(client):
    with patch("routes.subject_routes.delete_subject_db", return_value=True):
        resp = client.delete("/subjects/1")

    assert resp.status_code == 204


def test_delete_subject_not_found(client):
    with patch("routes.subject_routes.delete_subject_db", return_value=False):
        resp = client.delete("/subjects/1")

    assert resp.status_code == 404
