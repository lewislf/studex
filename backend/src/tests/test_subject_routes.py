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


# @pytest.fixture
# def client():
#     app = Flask(__name__)
#     app.register_blueprint(subject_bp)
#     return app.test_client()


def fake_subject(**kwargs):
    base = {
        "id": 1,
        "user_id": 10,
        "name": "Redes",
        "description": "Redes de Computadores",
        "domain": 55,
        "icon": "globe",
        "color": "#e63946",
        "date": "2026-07-05",
        "to_dict": lambda: {
            "id": 1,
            "title": "Redes",
            "description": "Redes de Computadores",
            "mastery_percentage": 55,
            "date": "2026-07-05",
        },
    }

    base.update(kwargs)

    # Atualiza o to_dict caso algum campo tenha sido sobrescrito
    base["to_dict"] = lambda: {
        "id": base["id"],
        "title": base["name"],
        "description": base["description"],
        "mastery_percentage": base["domain"],
        "date": base["date"],
    }

    return SimpleNamespace(**base)


def test_get_subjects(client):
    subjects = [
        fake_subject(id=1, name="Redes"),
        fake_subject(id=2, name="POO"),
    ]

    with patch(
        "routes.subject_routes.get_subjects_db",
        return_value=subjects,
    ) as mock_get, patch(
        "routes.subject_routes.match_subject_user_db",
        return_value=True,
    ):

        response = client.get("/users/10/subjects")

    assert response.status_code == 200

    body = response.get_json()

    assert len(body) == 2
    assert body[0]["id"] == 1
    assert body[0]["title"] == "Redes"
    assert body[1]["title"] == "POO"

    mock_get.assert_called_once_with(10)


def test_get_subjects_none(client):
    with patch(
        "routes.subject_routes.get_subjects_db",
        return_value=None,
    ):
        response = client.get("/users/10/subjects")

    assert response.status_code == 404


def test_get_subject(client):
    with patch(
        "routes.subject_routes.get_subject_db",
        return_value=fake_subject(),
    ), patch(
        "routes.subject_routes.match_subject_user_db",
        return_value=True,
    ):

        response = client.get("/users/10/subjects/1")

    assert response.status_code == 200

    body = response.get_json()

    assert body["id"] == 1
    assert body["title"] == "Redes"


def test_get_subject_not_found(client):
    with patch(
        "routes.subject_routes.get_subject_db",
        return_value=None,
    ):
        response = client.get("/users/10/subjects/1")

    assert response.status_code == 404


def test_create_subject(client):
    payload = {
        "user_id": 10,
        "name": "Redes",
        "description": "desc",
        "domain": 55,
        "icon": "globe",
        "color": "#e63946",
        "date": "2026-07-05",
    }

    with patch(
        "routes.subject_routes.save_subject_db",
        return_value=7,
    ) as mock_save:

        response = client.post(
            "/users/10/subjects",
            json=payload,
        )

    assert response.status_code == 201
    assert response.get_json() == {"id": 7}

    mock_save.assert_called_once_with(
        10,
        "Redes",
        "desc",
        55,
        "globe",
        "#e63946",
        "2026-07-05",
    )


def test_delete_subject_success(client):
    with patch(
        "routes.subject_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.subject_routes.delete_subject_db",
        return_value=True,
    ):

        response = client.delete("/users/10/subjects/1")

    assert response.status_code == 204


def test_delete_subject_not_found(client):
    with patch(
        "routes.subject_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.subject_routes.delete_subject_db",
        return_value=False,
    ):

        response = client.delete("/users/10/subjects/1")

    assert response.status_code == 404
