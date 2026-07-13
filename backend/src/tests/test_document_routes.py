"""
Testes unitários da rota de upload de documento.

Estilo do repo: o RAG/LLM e as funções `*_db` são
mockadas. Os testes cobrem o envio de arquivo (campo file, user_id, subject_id),
a decisão de armazenamento dos arquivos do usuário e a autorização de matéria
(bug de segurança: subject_id não pertencente ao user_id).
"""

from io import BytesIO
from unittest.mock import patch

import routes.document_routes as document_routes


def test_upload_persists_under_user_subject(client, tmp_path):
    materials = [{"tipo": "resumo", "titulo": "T", "conteudo": {}, "creation_date": "2026-07-07"}]

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=materials), \
         patch("routes.document_routes.match_subject_user_db", return_value=True), \
         patch("routes.document_routes.save_materials_db") as mock_save:

        response = client.post(
            "/users/10/documents",
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
                "user_id": "10",
                "subject_id": "3",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 201
    # Materiais do arquivo salvos na matéria (3) do usuário logado (10)
    mock_save.assert_called_once_with(3, materials)


def test_upload_rejects_subject_of_another_user(client, tmp_path):
    """Lacuna de autorização: subject_id de outro usuário não pode receber
    material via upload. match_subject_user_db devolvendo False -> 404, sem
    processar o PDF (load_documents nem deve ser chamado)."""
    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents") as mock_load, \
         patch("routes.document_routes.match_subject_user_db", return_value=False), \
         patch("routes.document_routes.save_materials_db") as mock_save:

        response = client.post(
            "/users/10/documents",
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
                "user_id": "10",
                "subject_id": "3",  # matéria de outro usuário
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 404
    assert response.get_json()["error"] == "User does not have this subject!"
    mock_load.assert_not_called()
    mock_save.assert_not_called()


def test_upload_missing_user_id_returns_400_before_saving_file(client, tmp_path):
    """Bug 5: sem o campo user_id, a rota devolvia 500 com o PDF já salvo em
    disco. Agora valida antes de tocar no filesystem."""
    with patch("routes.document_routes.DOCS_DIR", tmp_path):
        response = client.post(
            "/users/10/documents",
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
                # user_id ausente
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    assert "user_id" in response.get_json()["error"]
    # nada foi gravado em disco (tmp_path também hospeda o test.db/test.key
    # do fixture temp_db, então filtra só o que a rota poderia ter salvo)
    assert list(tmp_path.glob("*.pdf")) == []


def test_upload_non_numeric_user_id_returns_400(client, tmp_path):
    with patch("routes.document_routes.DOCS_DIR", tmp_path):
        response = client.post(
            "/users/10/documents",
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
                "user_id": "não-é-um-numero",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    assert list(tmp_path.glob("*.pdf")) == []


def test_upload_rejects_mismatched_user(client, tmp_path):
    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.save_materials_db") as mock_save:

        response = client.post(
            "/users/10/documents",
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula.pdf"),
                "user_id": "99",  # não bate com o id da URL
                "subject_id": "3",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    mock_save.assert_not_called()


def test_upload_saves_file_with_unique_name_on_disk(client, tmp_path):
    """Bug 6: dois uploads simultâneos do mesmo nome de arquivo não podem
    colidir no mesmo path em disco. O nome salvo carrega um prefixo uuid, o
    original vira sufixo (só pro filename retornado na resposta seguir
    "limpo")."""
    materials = [{"tipo": "resumo", "titulo": "T", "conteudo": {}, "creation_date": "2026-07-07"}]

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=materials), \
         patch("routes.document_routes.match_subject_user_db", return_value=True), \
         patch("routes.document_routes.save_materials_db"):

        response = client.post(
            "/users/10/documents",
            data={
                "file": (BytesIO(b"%PDF-1.4 fake"), "aula1.pdf"),
                "user_id": "10",
                "subject_id": "3",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 201
    # nome de exibição segue limpo na resposta
    assert response.get_json()["filename"] == "aula1.pdf"
    # mas o arquivo em disco tem um prefixo uuid, não "aula1.pdf" puro
    salvos = list(tmp_path.glob("*.pdf"))
    assert len(salvos) == 1
    assert salvos[0].name != "aula1.pdf"
    assert salvos[0].name.endswith("aula1.pdf")


# ---------------------------------------------------------------------------
# Progresso em memória: token por upload (bug 4 da auditoria)
# ---------------------------------------------------------------------------

def test_upload_rejects_non_pdf(client, tmp_path):
    with patch("routes.document_routes.DOCS_DIR", tmp_path):
        response = client.post(
            "/users/10/documents",
            data={
                "file": (BytesIO(b"nope"), "aula.txt"),
                "user_id": "10",
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
