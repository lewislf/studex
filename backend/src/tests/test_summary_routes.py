from types import SimpleNamespace
from unittest.mock import patch

import pytest

from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def fake_subject():
    return SimpleNamespace(
        id=2,
        name="Redes",
        user_id=10,
    )


def fake_summary():
    return SimpleNamespace(
        id=1,
        subject_id=2,
        titulo="Planolândia",
        conteudo='{"texto":"Resumo","topicos_chave":["A","B"]}',
        creation_date="2026-07-04",
        to_dict=lambda: {
            "id": 1,
            "tipo": "resumo",
            "titulo": "Planolândia",
            "creation_date": "2026-07-04",
            "conteudo": '{"texto":"Resumo","topicos_chave":["A","B"]}',
        },
    )


def test_get_summary(client):
    with patch(
        "routes.summary_routes.get_summary_db",
        return_value=fake_summary(),
    ), patch(
        "routes.summary_routes.get_subject_db",
        return_value=fake_subject(),
    ), patch(
        "routes.summary_routes.match_subject_user_db",
        return_value=True,
    ):
        response = client.get("/users/10/subjects/2/summaries/1")

    assert response.status_code == 200

    body = response.get_json()

    assert body["id"] == 1
    assert body["titulo"] == "Planolândia"
    assert body["conteudo"]["texto"] == "Resumo"
    assert body["conteudo"]["topicos_chave"] == ["A", "B"]


def test_get_summary_not_found(client):
    with patch(
        "routes.summary_routes.get_summary_db",
        return_value=None,
    ):
        response = client.get("/users/10/subjects/2/summaries/1")

    assert response.status_code == 404


def test_get_summaries(client):
    with patch(
        "routes.summary_routes.get_summaries_db",
        return_value=[fake_summary(), fake_summary()],
    ), patch(
        "routes.summary_routes.get_subject_db",
        return_value=fake_subject(),
    ), patch(
        "routes.summary_routes.match_subject_user_db",
        return_value=True,
    ):
        response = client.get("/users/10/subjects/2/summaries")

    assert response.status_code == 200

    body = response.get_json()

    assert len(body) == 2
    assert body[0]["conteudo"]["texto"] == "Resumo"
    assert body[1]["conteudo"]["topicos_chave"] == ["A", "B"]


def test_get_summaries_not_found(client):
    with patch(
        "routes.summary_routes.get_summaries_db",
        return_value=None,
    ):
        response = client.get("/users/10/subjects/2/summaries")

    assert response.status_code == 404


def test_create_summary(client):
    payload = {
        "title": "Planolândia",
        "creation_date": "2026-07-04",
        "conteudo": {
            "texto": "Resumo",
            "topicos_chave": ["A", "B"],
        },
    }

    with patch(
        "routes.summary_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.summary_routes.save_summary_db",
        return_value=7,
    ) as mock_save:
        response = client.post(
            "/users/10/subjects/2/summaries",
            json=payload,
        )

    assert response.status_code == 201
    assert response.get_json() == {"id": 7}

    mock_save.assert_called_once()


def test_delete_summary(client):
    with patch(
        "routes.summary_routes.get_summary_db",
        return_value=fake_summary(),
    ), patch(
        "routes.summary_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.summary_routes.delete_summary_db",
        return_value=True,
    ):
        response = client.delete("/users/10/subjects/2/summaries/1")

    assert response.status_code == 204


def test_delete_summary_not_found(client):
    with patch(
        "routes.summary_routes.get_summary_db",
        return_value=None,
    ), patch(
        "routes.summary_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.summary_routes.delete_summary_db",
        return_value=False,
    ):
        response = client.delete("/users/10/subjects/2/summaries/1")

    assert response.status_code == 404