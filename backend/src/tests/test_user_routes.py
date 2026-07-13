"""
Testes unitários da rota de autenticação (login).

As funções de banco (`*_db`) são substituídas por mocks. O test_client do Flask roda in-process.
"""

import sqlite3
from types import SimpleNamespace
from unittest.mock import patch


def fake_user(**kwargs):
    base = {"id": 1, "name": "Maria", "email": "maria@email.com"}
    base.update(kwargs)

    return SimpleNamespace(
        id=base["id"],
        to_dict=lambda: {
            "id": base["id"],
            "name": base["name"],
            "email": base["email"],
        }
    )


def test_login_success(client):
    fake_counters = {"summaries": 2, "mind_maps": 1}
    fake_gamification = {"current_streak": 3, "streak": 3}

    with patch(
        "routes.user_routes.login_user_db",
        return_value=fake_user(),
    ) as mock_login, patch(
        "routes.user_routes._live_counters",
        return_value=fake_counters,
    ) as mock_counters, patch(
        "routes.user_routes._gamification_with_streak",
        return_value=fake_gamification,
    ) as mock_gamification:

        response = client.post(
            "/users/login",
            json={"email": "maria@email.com", "password": "senha123"},
        )

    assert response.status_code == 200

    body = response.get_json()

    assert body == {
        "id": 1,
        "name": "Maria",
        "email": "maria@email.com",
        "counters": fake_counters,
        "gamification": fake_gamification,
    }
    mock_login.assert_called_once_with("maria@email.com", "senha123")
    mock_counters.assert_called_once_with(1)
    mock_gamification.assert_called_once()


def test_login_invalid_credentials(client):
    with patch(
        "routes.user_routes.login_user_db",
        return_value=None,
    ):
        response = client.post(
            "/users/login",
            json={"email": "maria@email.com", "password": "errada"},
        )

    assert response.status_code == 401


def test_login_missing_fields(client):
    response = client.post("/users/login", json={"email": "maria@email.com"})

    assert response.status_code == 400


def test_create_user_duplicate_email(client):
    # Email UNIQUE: cadastro duplicado deve virar 409, não 500.
    with patch(
        "routes.user_routes.save_user_db",
        side_effect=sqlite3.IntegrityError("UNIQUE constraint failed: users.email"),
    ):
        response = client.post(
            "/users",
            json={"name": "Maria", "email": "maria@email.com", "password": "senha123"},
        )

    assert response.status_code == 409


def test_delete_user_success(client):
    with patch(
        "routes.user_routes.delete_user_db",
        return_value=True,
    ), patch(
        "routes.user_routes.delete_vectors_by_metadata",
    ) as mock_delete_vectors:

        response = client.delete("/users/1")

    assert response.status_code == 204
    mock_delete_vectors.assert_called_once_with(user_id=1)


def test_delete_user_not_found(client):
    with patch(
        "routes.user_routes.delete_user_db",
        return_value=False,
    ):
        response = client.delete("/users/1")

    assert response.status_code == 404


def test_delete_user_qdrant_failure_does_not_block_204(client):
    """Erro na limpeza do Qdrant não pode impedir o delete de completar."""
    with patch(
        "routes.user_routes.delete_user_db",
        return_value=True,
    ), patch(
        "routes.user_routes.delete_vectors_by_metadata",
        side_effect=Exception("qdrant indisponível"),
    ):
        response = client.delete("/users/1")

    assert response.status_code == 204
