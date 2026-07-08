"""
Testes unitários da rota de upload de documento.

Estilo do repo: o RAG/LLM e as funções `*_db` são
mockadas. Os testes cobrem o envio de arquivo (campo file, user_id, subject_id) e a
decisão de armazenamento dos arquivos do usuário.
"""

from io import BytesIO
from unittest.mock import patch


def test_upload_persists_under_user_subject(client, tmp_path):
    materials = [{"tipo": "resumo", "titulo": "T", "conteudo": {}, "creation_date": "2026-07-07"}]

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=materials), \
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
