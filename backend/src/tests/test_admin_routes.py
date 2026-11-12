"""Testes das rotas /admin (status e backup) e da persistência configurável.

O fixture `client` (conftest) já aponta app.config["DB_PATH"] para um banco
temporário; é isso que as rotas /admin leem nos testes. Em produção vale o
DB_PATH do módulo (env STUDEX_DB_PATH).
"""

import contextlib
import sqlite3

import pytest

import routes.document_routes as document_routes
from database.database import init_db, save_user_db


def _admin(monkeypatch, uid=1):
    monkeypatch.setenv("ADMIN_USER_IDS", str(uid))
    # require_admin confere se o admin ainda existe (via DB_PATH padrão do
    # módulo); aqui o banco das rotas é temporário, então simulamos a busca.
    import database.database as db
    monkeypatch.setattr(db, "user_exists_db", lambda user_id, *a, **k: user_id == uid)


def test_status_requires_auth(client):
    assert client.get("/admin/status").status_code == 401


def test_status_forbidden_for_non_admin(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "99")
    assert client.get("/admin/status", headers=auth_headers(1)).status_code == 403


def test_status_ok_for_admin(client, auth_headers, monkeypatch, temp_db, tmp_path):
    _admin(monkeypatch)
    monkeypatch.setattr(document_routes, "DOCS_DIR", tmp_path / "docs")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / ".gitkeep").write_text("")
    (tmp_path / "docs" / "x.pdf").write_text("x")
    monkeypatch.setenv("STUDEX_PERSISTENT_DIR", str(tmp_path))
    save_user_db("Ana", "senha12345", "ana@x.com", db_path=temp_db)

    r = client.get("/admin/status", headers=auth_headers(1))
    assert r.status_code == 200
    body = r.get_json()
    assert body["users_count"] == 1
    assert body["db_created_at"]
    assert body["uploads_pending"] == 1
    assert body["path_is_under_persistent_dir"] is True
    assert body["persistent_dir"] == str(tmp_path)
    assert "ana@x.com" not in r.get_data(as_text=True)
    assert body["backend"] == "sqlite"
    assert body["db_size_bytes"] > 0


def test_status_turso_mode_does_not_touch_filesystem(client, auth_headers, monkeypatch, temp_db, tmp_path):
    import database.database as db
    _admin(monkeypatch)
    save_user_db("Ana", "senha12345", "ana@x.com", db_path=temp_db)
    monkeypatch.setattr(db, "BACKEND", "turso")
    monkeypatch.setattr(db, "describe_backend", lambda: {"backend": "turso", "location": "libsql://x.turso.io"})
    from main import app
    # caminho inexistente: no modo turso não pode ser consultado/criado
    ausente = tmp_path / "nao_existe.db"
    monkeypatch.setitem(app.config, "DB_PATH", ausente)
    # db_connection (fake do turso) ignora o arquivo e usa o banco temporário
    import contextlib as cl
    @cl.contextmanager
    def fake(db_path=None):
        c = sqlite3.connect(temp_db)
        try:
            yield c
        finally:
            c.close()
    monkeypatch.setattr(db, "db_connection", fake)
    body = client.get("/admin/status", headers=auth_headers(1)).get_json()
    assert body["backend"] == "turso" and body["location"] == "libsql://x.turso.io"
    assert body["db_size_bytes"] is None and body["db_path"] is None
    assert body["users_count"] == 1 and body["db_created_at"]
    assert not ausente.exists()


def test_backup_404_when_disabled(client, auth_headers, monkeypatch):
    _admin(monkeypatch)
    monkeypatch.delenv("ADMIN_BACKUP_ENABLED", raising=False)
    assert client.get("/admin/backup", headers=auth_headers(1)).status_code == 404


def test_backup_404_without_token_when_disabled(client, monkeypatch):
    monkeypatch.delenv("ADMIN_BACKUP_ENABLED", raising=False)
    assert client.get("/admin/backup").status_code == 404


def test_backup_404_when_db_missing(client, auth_headers, monkeypatch, tmp_path):
    _admin(monkeypatch)
    monkeypatch.setenv("ADMIN_BACKUP_ENABLED", "1")
    from main import app
    ausente = tmp_path / "nao_existe.db"
    monkeypatch.setitem(app.config, "DB_PATH", ausente)
    assert client.get("/admin/backup", headers=auth_headers(1)).status_code == 404
    assert not ausente.exists()


def test_status_path_with_special_chars(client, auth_headers, monkeypatch, tmp_path):
    _admin(monkeypatch)
    from main import app
    p = tmp_path / "a#b?c%d.db"
    init_db(db_path=p)
    monkeypatch.setitem(app.config, "DB_PATH", p)
    r = client.get("/admin/status", headers=auth_headers(1))
    assert r.status_code == 200 and r.get_json()["users_count"] == 0


def test_backup_auth(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ADMIN_BACKUP_ENABLED", "1")
    monkeypatch.setenv("ADMIN_USER_IDS", "99")
    assert client.get("/admin/backup").status_code == 401
    assert client.get("/admin/backup", headers=auth_headers(1)).status_code == 403


def test_backup_returns_valid_sqlite(client, auth_headers, monkeypatch, temp_db, tmp_path):
    _admin(monkeypatch)
    monkeypatch.setenv("ADMIN_BACKUP_ENABLED", "1")
    save_user_db("Ana", "senha12345", "ana@x.com", db_path=temp_db)
    save_user_db("Bia", "senha12345", "bia@x.com", db_path=temp_db)
    import tempfile
    tmpbase = tmp_path / "tmpbase"
    tmpbase.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmpbase))

    r = client.get("/admin/backup", headers=auth_headers(1))
    assert r.status_code == 200
    # nada do snapshot fica em disco
    assert list(tmpbase.iterdir()) == []
    assert r.headers["Cache-Control"] == "no-store"
    assert "studex-backup-" in r.headers["Content-Disposition"]
    out = tmp_path / "restored.db"
    out.write_bytes(r.data)
    r.close()
    conn = sqlite3.connect(out)
    try:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
        assert conn.execute("SELECT value FROM meta WHERE key='db_created_at'").fetchone()[0]
        # mesmas tabelas/índices e mesma contagem de linhas que a origem
        src = sqlite3.connect(temp_db)
        try:
            q = "SELECT name FROM sqlite_master WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%' ORDER BY name"
            assert [r[0] for r in conn.execute(q)] == [r[0] for r in src.execute(q)]
            for (t,) in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
                assert (conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                        == src.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]), t
        finally:
            src.close()
    finally:
        conn.close()


def test_init_db_creates_parent_dir_and_meta_stable(tmp_path):
    db = tmp_path / "sub" / "dir" / "u.db"
    init_db(db_path=db)
    c = sqlite3.connect(db)
    first = c.execute("SELECT value FROM meta WHERE key='db_created_at'").fetchone()[0]
    assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    c.close()
    init_db(db_path=db)  # reexecutar não muda db_created_at
    c = sqlite3.connect(db)
    assert c.execute("SELECT value FROM meta WHERE key='db_created_at'").fetchone()[0] == first
    c.close()


def test_status_reports_client_ip_source_without_ip(client, auth_headers, monkeypatch):
    _admin(monkeypatch)
    r = client.get("/admin/status", headers={**auth_headers(1), "CF-Connecting-IP": "203.0.113.7"})
    assert r.status_code == 200
    assert r.get_json()["client_ip_source"] == "CF-Connecting-IP"
    assert "203.0.113.7" not in r.get_data(as_text=True)
    r = client.get("/admin/status", headers={**auth_headers(1), "True-Client-IP": "203.0.113.7"})
    assert r.get_json()["client_ip_source"] == "remote_addr"  # True-Client-IP é ignorado


def test_backup_send_file_failure_closes_handle_and_500(client, auth_headers, monkeypatch):
    import routes.admin_routes as ar
    _admin(monkeypatch)
    monkeypatch.setenv("ADMIN_BACKUP_ENABLED", "1")
    abertos = []
    def falha(handle, **kw):
        abertos.append(handle)
        raise RuntimeError("boom")
    monkeypatch.setattr(ar, "send_file", falha)
    assert client.get("/admin/backup", headers=auth_headers(1)).status_code == 500
    assert abertos and abertos[0].closed
