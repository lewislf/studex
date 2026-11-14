from unittest.mock import MagicMock

import pytest

import routes.chat_routes  # noqa: F401  (coloca rag_api e qdrant no sys.path)
import chat
import qdrant_server


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(qdrant_server, "client", client)
    monkeypatch.setattr(qdrant_server, "_indexadas", set())
    return client


def test_indices_de_filtro_criados_uma_vez(fake_client):
    qdrant_server.ensure_payload_indexes()
    qdrant_server.ensure_payload_indexes()

    campos = [c.kwargs["field_name"] for c in fake_client.create_payload_index.call_args_list]
    assert campos == ["user_id", "subject_id"]  # só na primeira chamada


def test_delete_cria_indices_e_filtra_por_int(fake_client, monkeypatch):
    fake_client.collection_exists.return_value = True
    # troca os modelos do qdrant_client por tuplas, para conferir o filtro montado
    monkeypatch.setattr(qdrant_server, "MatchValue", lambda value: ("igual", value))
    monkeypatch.setattr(qdrant_server, "FieldCondition", lambda key, match: (key, match))
    monkeypatch.setattr(qdrant_server, "Filter", lambda must: must)

    qdrant_server.delete_vectors_by_metadata(user_id="10", subject_id=3)

    assert fake_client.create_payload_index.called
    filtro = fake_client.delete.call_args.kwargs["points_selector"]
    assert filtro == [("user_id", ("igual", 10)), ("subject_id", ("igual", 3))]


def test_delete_sem_colecao_nao_faz_nada(fake_client):
    fake_client.collection_exists.return_value = False
    qdrant_server.delete_vectors_by_metadata(user_id=10)
    fake_client.delete.assert_not_called()
    fake_client.create_payload_index.assert_not_called()


def test_busca_sem_colecao_volta_vazia(fake_client, monkeypatch):
    fake_client.collection_exists.return_value = False
    index = MagicMock()
    monkeypatch.setattr(chat, "_get_index", lambda: index)

    assert chat.buscar_trechos("oi", 1, 2) == []
    index.as_retriever.assert_not_called()


def test_busca_cria_indices_antes_de_filtrar(fake_client, monkeypatch):
    fake_client.collection_exists.return_value = True
    index = MagicMock()
    index.as_retriever.return_value.retrieve.return_value = ["trecho"]
    monkeypatch.setattr(chat, "_get_index", lambda: index)

    assert chat.buscar_trechos("oi", 1, 2) == ["trecho"]
    assert fake_client.create_payload_index.called
