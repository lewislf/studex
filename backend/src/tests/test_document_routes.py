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


# ---------------------------------------------------------------------------
# Dedup na rota de upload (flashcards, resumo e mapa mental)
# ---------------------------------------------------------------------------

def test_upload_dedup_descarta_todos_os_flashcards_retorna_207(client, tmp_path):
    """Caso especial: a geração produziu só um baralho, e o dedup descarta
    todos os cards por serem duplicados dos já existentes na matéria. Sem
    outros materiais pra salvar, a resposta é 207 com "error" avisando o
    motivo (o frontend mostra "error" de um 207 como aviso, não como falha
    dura)."""
    baralho = [{"tipo": "baralho", "titulo": "T", "conteudo": {"flashcards": [
        {"pergunta": "P1", "resposta": "R1"},
    ]}, "creation_date": "2026-07-07"}]

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=baralho), \
         patch("routes.document_routes.match_subject_user_db", return_value=True), \
         patch("routes.document_routes.get_flashcards_by_subject_db", return_value=[]), \
         patch("routes.document_routes.deduplicar_flashcards", return_value=[]), \
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

    assert response.status_code == 207
    body = response.get_json()
    assert "duplicad" in body["error"].lower()
    mock_save.assert_not_called()


def test_upload_resumo_duplicado_descartado_tudo_duplicado_retorna_207(client, tmp_path):
    """A geração produziu só um resumo, e o dedup lexical o descarta por ser
    quase-idêntico a um resumo já existente na matéria: nada sobra pra
    salvar, resposta é 207 com status "duplicate_materials"."""
    materiais_gerados = [{
        "tipo": "resumo", "titulo": "T", "conteudo": {"texto": "x", "topicos_chave": []},
        "creation_date": "2026-07-09",
    }]

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=materiais_gerados), \
         patch("routes.document_routes.match_subject_user_db", return_value=True), \
         patch("routes.document_routes.get_summaries_db", return_value=["algo existente"]), \
         patch("routes.document_routes.filtrar_materiais_duplicados", return_value=[]), \
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

    assert response.status_code == 207
    body = response.get_json()
    assert body["status"] == "duplicate_materials"
    assert "duplicad" in body["error"].lower()
    mock_save.assert_not_called()


def test_upload_resumo_duplicado_mapa_mental_novo_salva_parcial_201(client, tmp_path):
    """Só o resumo é duplicado, o mapa mental sobrevive. Resposta continua
    201, mas sem o resumo em "materiais"."""
    resumo_dup = {
        "tipo": "resumo", "titulo": "T", "conteudo": {"texto": "x", "topicos_chave": []},
        "creation_date": "2026-07-09",
    }
    mapa_novo = {
        "tipo": "mapa_mental", "titulo": "T — Mapa Mental de Estudo",
        "conteudo": {"nodes": [], "edges": []}, "creation_date": "2026-07-09",
    }
    materiais_gerados = [resumo_dup, mapa_novo]

    def _fake_filtrar(materiais_novos, materiais_existentes, tipo, threshold=None):
        if tipo == "resumo":
            return []  # descartado: duplicado
        return materiais_novos  # mapa mental sobrevive

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=materiais_gerados), \
         patch("routes.document_routes.match_subject_user_db", return_value=True), \
         patch("routes.document_routes.get_summaries_db", return_value=["algo existente"]), \
         patch("routes.document_routes.get_mindmaps_db", return_value=[]), \
         patch("routes.document_routes.filtrar_materiais_duplicados", side_effect=_fake_filtrar), \
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
    body = response.get_json()
    assert [m["tipo"] for m in body["materiais"]] == ["mapa_mental"]
    mock_save.assert_called_once_with(3, [mapa_novo])


def test_upload_dedup_resumo_mapa_falha_nao_bloqueia_salvar(client, tmp_path):
    """Mesmo princípio do dedup de flashcards: falha no dedup de
    resumo/mapa mental nunca pode impedir de salvar. Salva com o material
    original, sem dedup."""
    materiais_gerados = [{
        "tipo": "resumo", "titulo": "T", "conteudo": {"texto": "x", "topicos_chave": []},
        "creation_date": "2026-07-09",
    }]

    with patch("routes.document_routes.DOCS_DIR", tmp_path), \
         patch("routes.document_routes.load_documents"), \
         patch("routes.document_routes.split_into_nodes"), \
         patch("routes.document_routes.build_vector_index"), \
         patch("routes.document_routes.generate_materials", return_value=materiais_gerados), \
         patch("routes.document_routes.match_subject_user_db", return_value=True), \
         patch("routes.document_routes.get_summaries_db", side_effect=RuntimeError("banco fora do ar")), \
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
    mock_save.assert_called_once_with(3, materiais_gerados)
