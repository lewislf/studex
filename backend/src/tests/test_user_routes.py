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
        to_dict=lambda: {
            "id": base["id"],
            "name": base["name"],
            "email": base["email"],
        }
    )


def test_login_success(client):
    with patch(
        "routes.user_routes.login_user_db",
        return_value=fake_user(),
    ) as mock_login:

        response = client.post(
            "/users/login",
            json={"email": "maria@email.com", "password": "senha123"},
        )

    assert response.status_code == 200

    body = response.get_json()

    assert body == {"id": 1, "name": "Maria", "email": "maria@email.com"}
    mock_login.assert_called_once_with("maria@email.com", "senha123")


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
