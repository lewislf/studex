from datetime import date

import pytest

from main import app
from database.database import save_user_db, save_subject_db, save_deck_db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_lista_baralhos_de_todas_as_materias_so_do_usuario(client, auth_headers):
    hoje = date.today().isoformat()
    ana = save_user_db("Ana", "senha-forte-123", "ana@x.com")
    bia = save_user_db("Bia", "senha-forte-123", "bia@x.com")
    grafos = save_subject_db(ana, "Grafos", "d", 0, "graph", "#f00", hoje)
    redes = save_subject_db(ana, "Redes", "d", 0, "network", "#0f0", hoje)
    alheia = save_subject_db(bia, "Outra", "d", 0, "x", "#000", hoje)
    d1 = save_deck_db(grafos, "Coloração", 0, 3, 1, 2, hoje)
    d2 = save_deck_db(redes, "TCP", 0, 0, 0, 5, hoje)
    save_deck_db(alheia, "Não é da Ana", 0, 9, 9, 9, hoje)

    r = client.get(f"/users/{ana}/decks", headers=auth_headers(ana))

    assert r.status_code == 200
    decks = {d["id"]: d for d in r.get_json()}
    assert set(decks) == {d1, d2}
    assert (decks[d1]["subject_name"], decks[d1]["subject_icon"], decks[d1]["subject_color"]) == ("Grafos", "graph", "#f00")
    assert (decks[d1]["new"], decks[d1]["learning"], decks[d1]["review"], decks[d1]["total_cards"]) == (3, 1, 2, 6)
    assert decks[d2]["subject_id"] == redes


def test_sem_baralhos_lista_vazia(client, auth_headers):
    uid = save_user_db("Ana", "senha-forte-123", "ana@x.com")
    r = client.get(f"/users/{uid}/decks", headers=auth_headers(uid))
    assert r.status_code == 200 and r.get_json() == []


def test_baralhos_de_outro_usuario_bloqueado(client, auth_headers):
    ana = save_user_db("Ana", "senha-forte-123", "ana@x.com")
    bia = save_user_db("Bia", "senha-forte-123", "bia@x.com")
    r = client.get(f"/users/{ana}/decks", headers=auth_headers(bia))
    assert r.status_code in (401, 403)
