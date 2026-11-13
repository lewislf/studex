from datetime import date
from unittest.mock import patch

import pytest

from main import app
from database.database import save_user_db, save_subject_db, get_chat_messages_db

RESPOSTA = {"answer": "É uma coloração com k cores [1].",
            "sources": [{"n": 1, "file_name": "grafos.pdf", "score": 0.8, "excerpt": "..."}]}


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False
    with app.test_client() as c:
        yield c


@pytest.fixture
def dono():
    """Dois usuários no banco isolado do teste; o primeiro com uma matéria."""
    uid = save_user_db("Ana", "senha-forte-123", "ana@x.com")
    outro = save_user_db("Bia", "senha-forte-123", "bia@x.com")
    sid = save_subject_db(uid, "Grafos", "d", 0, "i", "#f00", date.today())
    return uid, outro, sid


def _criar(client, auth_headers, uid, sid):
    r = client.post(f"/users/{uid}/chats", json={"subject_id": sid}, headers=auth_headers(uid))
    assert r.status_code == 201
    return r.get_json()["id"]


def test_criar_listar_e_conversar(client, auth_headers, dono):
    uid, _, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)

    with patch("routes.chat_routes.responder", return_value=RESPOSTA) as resp:
        r = client.post(f"/users/{uid}/chats/{chat_id}/messages",
                        json={"question": "  O que é k-coloração?  "}, headers=auth_headers(uid))
    assert r.status_code == 200
    assert r.get_json() == RESPOSTA
    # primeira pergunta: histórico vazio
    resp.assert_called_once_with("O que é k-coloração?", uid, sid, [])

    chats = client.get(f"/users/{uid}/chats", headers=auth_headers(uid)).get_json()
    assert chats[0]["titulo"] == "O que é k-coloração?"
    assert chats[0]["materia_nome"] == "Grafos"

    chat = client.get(f"/users/{uid}/chats/{chat_id}", headers=auth_headers(uid)).get_json()
    assert chat["materia_nome"] == "Grafos" and chat["materia_cor"] == "#f00"
    assert [m["papel"] for m in chat["mensagens"]] == ["user", "assistant"]
    assert chat["mensagens"][1]["sources"][0]["file_name"] == "grafos.pdf"


def test_lista_vazia_e_200(client, auth_headers, dono):
    uid, _, _ = dono
    r = client.get(f"/users/{uid}/chats", headers=auth_headers(uid))
    assert r.status_code == 200 and r.get_json() == []


@pytest.mark.parametrize("body", [{}, {"subject_id": "2"}, {"subject_id": True}])
def test_criar_subject_invalido_400(client, auth_headers, dono, body):
    uid, _, _ = dono
    assert client.post(f"/users/{uid}/chats", json=body, headers=auth_headers(uid)).status_code == 400


def test_criar_em_materia_de_outro_404(client, auth_headers, dono):
    _, outro, sid = dono
    r = client.post(f"/users/{outro}/chats", json={"subject_id": sid}, headers=auth_headers(outro))
    assert r.status_code == 404


def test_outro_usuario_nao_ve_nem_usa_nem_apaga(client, auth_headers, dono):
    uid, outro, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)
    h = auth_headers(outro)
    assert client.get(f"/users/{outro}/chats/{chat_id}", headers=h).status_code == 404
    with patch("routes.chat_routes.responder") as resp:
        r = client.post(f"/users/{outro}/chats/{chat_id}/messages", json={"question": "oi"}, headers=h)
    assert r.status_code == 404 and not resp.called
    assert client.delete(f"/users/{outro}/chats/{chat_id}", headers=h).status_code == 404
    assert client.get(f"/users/{uid}/chats/{chat_id}", headers=auth_headers(uid)).status_code == 200


@pytest.mark.parametrize("question", [None, 123, "   ", "x" * 1001], ids=["ausente", "numero", "vazia", "longa"])
def test_pergunta_invalida_400(client, auth_headers, dono, question):
    uid, _, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)
    r = client.post(f"/users/{uid}/chats/{chat_id}/messages",
                    json={"question": question}, headers=auth_headers(uid))
    assert r.status_code == 400


def test_falha_do_llm_503_sem_salvar(client, auth_headers, dono):
    uid, _, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)
    with patch("routes.chat_routes.responder", side_effect=RuntimeError("503 UNAVAILABLE")):
        r = client.post(f"/users/{uid}/chats/{chat_id}/messages",
                        json={"question": "oi"}, headers=auth_headers(uid))
    assert r.status_code == 503
    assert get_chat_messages_db(chat_id) == []


def test_apagar_chat_204(client, auth_headers, dono):
    uid, _, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)
    assert client.delete(f"/users/{uid}/chats/{chat_id}", headers=auth_headers(uid)).status_code == 204
    assert client.get(f"/users/{uid}/chats/{chat_id}", headers=auth_headers(uid)).status_code == 404


def test_limite_de_perguntas_429(client, auth_headers, dono, monkeypatch):
    uid, _, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)
    monkeypatch.setenv("RATELIMIT_CHAT_USER_MAX", "2")
    app.config["RATELIMIT_ENABLED"] = True
    try:
        with patch("routes.chat_routes.responder", return_value=RESPOSTA):
            codes = [client.post(f"/users/{uid}/chats/{chat_id}/messages",
                                 json={"question": "oi"}, headers=auth_headers(uid)).status_code
                     for _ in range(3)]
    finally:
        app.config["RATELIMIT_ENABLED"] = False
    assert codes == [200, 200, 429]


def test_historico_vai_para_o_responder(client, auth_headers, dono):
    uid, _, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)
    url = f"/users/{uid}/chats/{chat_id}/messages"

    with patch("routes.chat_routes.responder", return_value=RESPOSTA) as resp:
        client.post(url, json={"question": "Quais os tipos?"}, headers=auth_headers(uid))
        client.post(url, json={"question": "E o segundo?"}, headers=auth_headers(uid))

    pergunta, _, _, historico = resp.call_args.args
    assert pergunta == "E o segundo?"
    # a pergunta atual não entra no histórico; só a troca anterior
    assert [(m["papel"], m["msg"]) for m in historico] == [
        ("user", "Quais os tipos?"), ("assistant", RESPOSTA["answer"]),
    ]


def test_historico_limitado_as_6_ultimas(client, auth_headers, dono):
    uid, _, sid = dono
    chat_id = _criar(client, auth_headers, uid, sid)
    url = f"/users/{uid}/chats/{chat_id}/messages"

    with patch("routes.chat_routes.responder", return_value=RESPOSTA) as resp:
        for i in range(5):
            client.post(url, json={"question": f"pergunta {i}"}, headers=auth_headers(uid))

    historico = resp.call_args.args[3]
    assert len(historico) == 6
    assert historico[0]["msg"] == "pergunta 1"   # as mais antigas ficaram de fora
    assert historico[-1]["papel"] == "assistant"
