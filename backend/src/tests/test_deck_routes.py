from types import SimpleNamespace
from unittest.mock import patch

def fake_deck():
    return SimpleNamespace(
        id=1,
        subject_id=2,
        titulo="TCP/IP",
        acuracia=90,
        novos=10,
        aprendendo=5,
        review=20,
        date="2026-06-05",
        to_dict=lambda: {
            "id": 1,
            "subtitle": "TCP/IP",
            "acuracy": 90,
            "date": "2026-06-05",
            "new": 10,
            "learning": 5,
            "review": 20,
            "total_cards": 35,
        },
    )


def fake_subject():
    return SimpleNamespace(
        id=2,
        name="Redes",
    )


def test_get_deck(client):
    print(client.application.url_map)

    for rule in client.application.url_map.iter_rules():
        print(rule)

    with patch(
        "routes.deck_routes.match_subject_user_db",
        return_value=True,
    ), patch(
        "routes.deck_routes.get_deck_db",
        return_value=fake_deck(),
    ), patch(
        "routes.deck_routes.get_subject_db",
        return_value=fake_subject(),
    ):
        response = client.get("/users/10/subjects/2/decks/1")

    print(response.status_code)
    print(response.get_json())
    assert response.status_code == 200

    body = response.get_json()

    assert body["id"] == 1
    assert body["subtitle"] == "TCP/IP"
    assert body["subject_name"] == "Redes"