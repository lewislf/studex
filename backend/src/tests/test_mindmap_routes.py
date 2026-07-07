from types import SimpleNamespace
from unittest.mock import patch

import json


def fake_mindmap(**kwargs):
    base = {
        "id": 1,
        "subject_id": 1,
        "titulo": "Planolândia",
        "date": "2026-07-04",
        "conteudo": json.dumps({
            "nodes": [],
            "edges": [],
        }),
        "to_dict": lambda: {
            "id": 1,
            "tipo": "mapa_mental",
            "titulo": "Planolândia",
            "creation_date": "2026-07-04",
            "conteudo": {
                "nodes": [],
                "edges": [],
            },
        },
    }

    base.update(kwargs)

    base["to_dict"] = lambda: {
        "id": base["id"],
        "tipo": "mapa_mental",
        "titulo": base["titulo"],
        "creation_date": base["date"],
        "conteudo": {
            "nodes": [],
            "edges": [],
        },
    }


    return SimpleNamespace(**base)


def test_get_mindmaps(client):
    mindmaps = [
        fake_mindmap(id=1, titulo="Mapa 1"),
        fake_mindmap(id=2, titulo="Mapa 2"),
    ]

    with patch(
        "routes.mindmap_routes.get_mindmaps_db",
        return_value=mindmaps,
    ), patch(
        "routes.mindmap_routes.get_subject_db",
        return_value=SimpleNamespace(id=1),
    ), patch(
        "routes.mindmap_routes.match_subject_user_db",
        return_value=True,
    ):

        response = client.get("/users/10/subjects/1/mindmaps")

    assert response.status_code == 200

    body = response.get_json()

    assert len(body) == 2
    assert body[0]["titulo"] == "Mapa 1"
    assert body[1]["titulo"] == "Mapa 2"


def test_get_mindmaps_not_found(client):
    with patch(
        "routes.mindmap_routes.get_mindmaps_db",
        return_value=None,
    ):

        response = client.get("/users/10/subjects/1/mindmaps")

    assert response.status_code == 404


def test_get_mindmap(client):
    with patch(
        "routes.mindmap_routes.get_mindmap_db",
        return_value=fake_mindmap(),
    ), patch(
        "routes.mindmap_routes.get_subject_db",
        return_value=SimpleNamespace(id=1),
    ), patch(
        "routes.mindmap_routes.match_subject_user_db",
        return_value=True,
    ):

        response = client.get("/users/10/subjects/1/mindmaps/1")

    assert response.status_code == 200

    body = response.get_json()

    assert body["id"] == 1
    assert body["titulo"] == "Planolândia"


def test_get_mindmap_not_found(client):
    with patch(
        "routes.mindmap_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.mindmap_routes.get_mindmap_db",
        return_value=None,
    ):

        response = client.get("/users/10/subjects/1/mindmaps/1")

    assert response.status_code == 404


def test_create_mindmap(client):
    payload = {
        "tipo": "mapa_mental",
        "titulo": "Planolândia",
        "creation_date": "2026-07-04",
        "conteudo": {
            "nodes": [],
            "edges": [],
        },
    }

    with patch(
        "routes.mindmap_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.mindmap_routes.save_mindmap_db",
        return_value=7,
    ) as mock_save:

        response = client.post(
            "/users/10/subjects/1/mindmaps",
            json=payload,
        )

    assert response.status_code == 201
    assert response.get_json() == {"id": 7}

    args = mock_save.call_args.kwargs

    assert args["subject_id"] == 1
    assert args["titulo"] == "Planolândia"
    assert args["creation_date"] == "2026-07-04"
    assert json.loads(args["conteudo"]) == payload["conteudo"]


def test_delete_mindmap_success(client):
    with patch(
        "routes.mindmap_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.mindmap_routes.get_mindmap_db",
        return_value=fake_mindmap(),
    ), patch(
        "routes.mindmap_routes.delete_mindmap_db",
        return_value=True,
    ):

        response = client.delete("/users/10/subjects/1/mindmaps/1")

    assert response.status_code == 204


def test_delete_mindmap_not_found(client):
    with patch(
        "routes.mindmap_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.mindmap_routes.get_mindmap_db",
        return_value=None,
    ), patch(
        "routes.mindmap_routes.delete_mindmap_db",
        return_value=False,
    ):

        response = client.delete("/users/10/subjects/1/mindmaps/1")

    assert response.status_code == 404