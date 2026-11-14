"""Modo "turso" simulado: driver libsql falso que recusa tudo que não é seguro."""

import json
import sqlite3
import sys
import threading
import types
from datetime import date

import pytest

import database.database as db
import fake_libsql  # mesmo diretório (conftest/rootdir no sys.path)

TOKEN = "SEGREDO-token-jwt-123"
URL = "libsql://meu-banco-org.turso.io?authToken=nao-deve-vazar"
TABELAS = ("subjects", "summaries", "decks", "flashcards", "mind_maps", "activity_days")


@pytest.fixture
def turso(monkeypatch, tmp_path):
    """Liga o modo turso com o libsql falso (instalado só aqui, via sys.modules)."""
    fake_libsql.db_file = str(tmp_path / "turso_fake.db")
    fake_libsql.stats.__init__()
    fake_libsql.autocommit = False
    mod = types.ModuleType("libsql")
    mod.connect = fake_libsql.connect
    monkeypatch.setitem(sys.modules, "libsql", mod)
    monkeypatch.setenv("TURSO_DATABASE_URL", URL)
    monkeypatch.setenv("TURSO_AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(db, "BACKEND", "turso")
    monkeypatch.setattr(db, "_turso_conn", None)
    db.init_db()
    yield fake_libsql
    db._drop_turso_conn()
    fake_libsql.autocommit = False


def _raw():
    """Conexão sqlite3 direta ao arquivo do fake, para verificar o estado real."""
    return sqlite3.connect(fake_libsql.db_file)


def test_init_db_and_lazy_connect(turso):
    tabelas = {r[0] for r in _raw().execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "subjects", "summaries", "decks", "flashcards", "mind_maps",
            "activity_days", "meta"} <= tabelas
    assert len(turso.stats.connect_calls) == 1  # conexão compartilhada
    call = turso.stats.connect_calls[0]
    assert call["database"] == URL and call["auth_token"] == TOKEN
    # nenhum SQL proibido foi emitido
    assert not any(s.strip().upper().startswith("BEGIN") for s in turso.stats.statements)
    assert db.BACKEND == "turso"
    db.init_db()  # idempotente


def test_signup_login_case_insensitive(turso):
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    assert isinstance(uid, int)
    assert db.user_exists_db(uid) is True
    assert db.user_exists_db(uid + 99) is False
    assert db.login_user_db("ana@x.com", "senha12345").id == uid
    assert db.login_user_db("  ANA@X.com ", "senha12345").id == uid
    assert db.login_user_db("ana@x.com", "errada") is None
    assert db.get_user_db(uid).email == "ana@x.com"
    assert db.count_people_db() == 1
    assert [u.id for u in db.get_users_db("An")] == [uid]
    with pytest.raises(sqlite3.IntegrityError):
        db.save_user_db("Outra", "senha12345", "ANA@x.com")
    with pytest.raises(sqlite3.IntegrityError):
        db.save_user_db("Outra", "senha12345", "ana@x.com")
    assert db.count_people_db() == 1


def _popular(uid):
    sid = db.save_subject_db(uid, "Mat", "d", 1, "i", "c", date(2026, 1, 1))
    resumo = db.save_summary_db(sid, "t", "c", date(2026, 1, 1))
    mapa = db.save_mindmap_db(sid, "m", "{}", date(2026, 1, 1))
    did = db.save_deck_db(sid, "b", 0, 1, 0, 0, date(2026, 1, 1))
    fid = db.save_flashcard_db(did, "p", "r", "novo", date(2026, 1, 1), embedding=[0.1, 0.2])
    db.record_activity_db(uid, "2026-01-01")
    db.record_activity_db(uid, "2026-01-01")
    return sid, resumo, mapa, did, fid


def test_crud_subject_deck_flashcard_summary_mindmap(turso):
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    sid, resumo, mapa, did, fid = _popular(uid)

    assert db.get_subject_db(sid).name == "Mat"
    assert [s.id for s in db.get_subjects_db(uid)] == [sid]
    assert db.count_subjects_db(uid) == 1
    assert db.match_subject_user_db(sid, uid) is True
    assert db.get_summary_db(resumo).titulo == "t"
    assert db.count_summaries_db(sid) == 1
    assert db.get_mindmap_db(mapa).titulo == "m"
    assert db.count_mindmaps_db(sid) == 1
    assert db.get_deck_db(did).titulo == "b"
    assert db.count_deck_db(sid) == 1
    assert db.get_flashcard_db(fid).embedding == [0.1, 0.2]
    assert db.count_flashcards_db(did) == 1
    assert db.count_flashcards_by_user_db(uid) == 1
    assert db.count_due_flashcards_db(uid, date(2026, 1, 2)) == 1
    assert len(db.get_flashcards_by_subject_db(sid)) == 1
    assert len(db.get_study_queue_db(did)) == 1
    assert len(db.get_user_study_queue_db(uid)) == 1
    assert db.get_activity_days_db(uid, "2026-01-01") == {"2026-01-01": 2}

    db.update_flashcard_review_db(fid, "review", "2026-01-01", 1.0, 2.5, 1, 0)
    db.update_flashcard_embedding_db(fid, [9.0])
    db.refresh_deck_counters_db(did)
    assert db.get_deck_db(did).review == 1
    assert db.get_flashcard_db(fid).embedding == [9.0]

    # save_materials_db: transação única; erro no meio faz rollback total
    mats = [{"tipo": "baralho", "titulo": "B2", "creation_date": date(2026, 1, 1),
             "conteudo": {"flashcards": [{"pergunta": "p", "resposta": "r"}]}},
            {"tipo": "resumo", "titulo": "R2", "creation_date": date(2026, 1, 1), "conteudo": {"a": 1}}]
    db.save_materials_db(sid, mats)
    assert db.count_deck_db(sid) == 2 and db.count_summaries_db(sid) == 2
    with pytest.raises(ValueError):
        db.save_materials_db(sid, mats[:1] + [{"tipo": "x"}])
    assert db.count_deck_db(sid) == 2  # nada do lote falho foi gravado

    # deletes devolvem True/False sem rowcount
    assert db.delete_flashcard_db(fid) is True
    assert db.delete_flashcard_db(fid) is False
    assert db.delete_summary_db(resumo) is True and db.delete_summary_db(resumo) is False
    assert db.delete_mindmap_db(mapa) is True and db.delete_mindmap_db(mapa) is False
    assert db.delete_deck_db(did) is True and db.delete_deck_db(did) is False
    assert db.delete_subject_db(sid) is True and db.delete_subject_db(sid) is False


def test_delete_deck_and_subject_cascade_without_fk(turso):
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    sid, resumo, mapa, did, fid = _popular(uid)
    raw = _raw()
    assert raw.execute("PRAGMA foreign_keys").fetchone()[0] == 0  # FK realmente off
    assert db.delete_deck_db(did) is True
    assert raw.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0] == 0
    assert db.delete_subject_db(sid) is True
    for t in ("summaries", "decks", "mind_maps", "subjects"):
        assert raw.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0, t


def test_delete_user_erasure_with_fk_ignored(turso):
    ana = db.save_user_db("Ana", "senha12345", "ana@x.com")
    bia = db.save_user_db("Bia", "senha12345", "bia@x.com")
    _popular(ana)
    _popular(bia)
    raw = _raw()
    assert raw.execute("PRAGMA foreign_keys").fetchone()[0] == 0

    assert db.delete_user_db(ana) is True
    assert db.delete_user_db(ana) is False
    for t in TABELAS:
        # nada da Ana sobrou; a Bia permanece intacta
        assert raw.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 1, t
    assert raw.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert raw.execute("SELECT COUNT(*) FROM subjects WHERE user_id=?", (ana,)).fetchone()[0] == 0
    assert raw.execute("SELECT COUNT(*) FROM activity_days WHERE user_id=?", (ana,)).fetchone()[0] == 0

    assert db.delete_user_db(bia) is True
    for t in TABELAS + ("users",):
        assert raw.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0, t


def test_concurrent_threads_are_serialised(turso):
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    erros = []

    def work(i):
        try:
            for j in range(5):
                sid = db.save_subject_db(uid, f"m{i}-{j}", "d", 1, "i", "c", date(2026, 1, 1))
                assert db.get_subject_db(sid).name == f"m{i}-{j}"
                db.record_activity_db(uid, "2026-01-01")
        except Exception as exc:  # noqa: BLE001
            erros.append(exc)

    ts = [threading.Thread(target=work, args=(i,)) for i in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert erros == []
    assert db.count_subjects_db(uid) == 40
    assert db.get_activity_days_db(uid, "2026-01-01") == {"2026-01-01": 40}
    assert turso.stats.max_active == 1  # nunca duas operações simultâneas no driver
    assert len(turso.stats.connect_calls) == 1


def test_connection_dropped_after_error_and_reconnects(turso):
    with pytest.raises(RuntimeError):
        with db.db_connection() as conn:
            conn.execute("SELECT 1")
            raise RuntimeError("stream expirou")
    assert db._turso_conn is None
    assert db.count_people_db() == 0
    assert len(turso.stats.connect_calls) == 2


def test_integrity_error_keeps_connection(turso):
    db.save_user_db("Ana", "senha12345", "ana@x.com")
    with pytest.raises(sqlite3.IntegrityError):
        db.save_user_db("Ana2", "senha12345", "ana@x.com")
    assert len(turso.stats.connect_calls) == 1


def test_exception_rolls_back(turso):
    with pytest.raises(ValueError):
        with db.db_connection() as conn:
            conn.execute("INSERT INTO meta(key, value) VALUES('k', 'v')")
            raise ValueError("falha")
    assert _raw().execute("SELECT COUNT(*) FROM meta WHERE key='k'").fetchone()[0] == 0


def test_describe_backend_never_leaks_token(turso, caplog):
    import logging
    with caplog.at_level(logging.DEBUG):
        db.init_db()
    info = db.describe_backend()
    assert info == {"backend": "turso", "location": "meu-banco-org.turso.io"}
    blob = json.dumps(info) + caplog.text
    assert TOKEN not in blob and "nao-deve-vazar" not in blob and "authToken" not in blob
    assert "libsql://" not in blob


def test_signup_and_login_routes(turso, client):
    r = client.post("/users", json={"name": "Ana", "email": "Ana@X.com", "password": "senha12345"})
    assert r.status_code == 201, r.get_json()
    r = client.post("/users", json={"name": "Ana", "email": "ana@x.com", "password": "senha12345"})
    assert r.status_code == 409
    r = client.post("/users/login", json={"email": "ANA@x.com", "password": "senha12345"})
    assert r.status_code == 200


def test_sqlite_mode_describe_backend(tmp_path):
    info = db.describe_backend()
    assert info["backend"] == "sqlite" and info["location"].endswith("users.db")


def test_sqlite_db_connection_commits_rolls_back_and_closes(temp_db):
    with db.db_connection(temp_db) as conn:
        conn.execute("INSERT INTO meta(key, value) VALUES('a', '1')")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")  # conexão foi fechada
    with pytest.raises(ValueError):
        with db.db_connection(temp_db) as conn:
            conn.execute("INSERT INTO meta(key, value) VALUES('b', '1')")
            raise ValueError
    with db.db_connection(temp_db) as conn:
        chaves = {r[0] for r in conn.execute("SELECT key FROM meta")}
    assert "a" in chaves and "b" not in chaves


def _smoke():
    """Carrega scripts/turso_smoke.py (não é pacote) sem executar o fluxo."""
    import importlib.util
    from pathlib import Path
    caminho = Path(__file__).resolve().parents[3] / "scripts" / "turso_smoke.py"
    spec = importlib.util.spec_from_file_location("turso_smoke_mod", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_smoke_atomicidade_passa_no_fake_transacional(turso):
    ok, det = _smoke().verificar_atomicidade(db)
    assert ok, det


def test_smoke_atomicidade_falha_com_driver_autocommit(turso):
    turso.autocommit = True
    smoke = _smoke()
    ok, det = smoke.verificar_atomicidade(db)
    assert not ok
    assert "NÃO faça o deploy" in det and "parciais" in det
    # resíduo foi limpo
    assert _raw().execute("SELECT COUNT(*) FROM meta WHERE key LIKE 'smoke_atomicidade_%'").fetchone()[0] == 0


def test_smoke_mascara_token_nos_detalhes(monkeypatch):
    smoke = _smoke()
    monkeypatch.setenv("TURSO_AUTH_TOKEN", TOKEN)
    smoke._resultados.clear()
    smoke.check("x", False, f"erro com {TOKEN} dentro")
    assert TOKEN not in smoke._resultados[0][2] and "***" in smoke._resultados[0][2]
    smoke._resultados.clear()


def test_execute_do_fake_devolve_none_e_cursor_sem_fetchmany(turso):
    with db.db_connection() as conn:
        cur = conn.cursor()
        assert cur.execute("SELECT 1") is None
        assert cur.fetchone() == (1,)
        with pytest.raises(AttributeError):
            cur.fetchmany(1)


def test_nested_db_connection_only_outer_commits(turso):
    def interno():
        with db.db_connection() as c:
            cur = c.cursor()
            cur.execute("INSERT INTO meta(key, value) VALUES('interno', '1')")

    with pytest.raises(RuntimeError):
        with db.db_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO meta(key, value) VALUES('externo', '1')")
            interno()
            raise RuntimeError("falha depois do bloco interno")
    chaves = {r[0] for r in _raw().execute("SELECT key FROM meta")}
    assert "externo" not in chaves and "interno" not in chaves
    assert db.count_people_db() == 0  # conexão se recupera e depth voltou a 0

    with db.db_connection() as conn:  # caminho feliz: tudo persiste
        conn.cursor().execute("INSERT INTO meta(key, value) VALUES('ok', '1')")
        interno()
    chaves = {r[0] for r in _raw().execute("SELECT key FROM meta")}
    assert {"ok", "interno"} <= chaves


def test_admin_backup_in_turso_mode(turso, client, auth_headers, monkeypatch, tmp_path):
    from test_admin_routes import _admin
    import routes.admin_routes as admin_routes
    _admin(monkeypatch)
    monkeypatch.setenv("ADMIN_BACKUP_ENABLED", "1")
    monkeypatch.setattr(admin_routes, "_CHUNK", 2)  # força várias páginas
    uids = [db.save_user_db(f"U{i}", "senha12345", f"u{i}@x.com") for i in range(5)]
    for u in uids[:2]:
        _popular(u)
    r = client.get("/admin/backup", headers=auth_headers(1))
    assert r.status_code == 200, r.data
    arq = tmp_path / "bk.db"
    arq.write_bytes(r.data)
    assert TOKEN.encode() not in r.data and b"nao-deve-vazar" not in r.data
    bk = sqlite3.connect(arq)
    orig = _raw()
    tabelas = [x[0] for x in orig.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    assert "users" in tabelas
    for t in tabelas:
        assert bk.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == \
            orig.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], t
    assert bk.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 5
    # conteúdo idêntico, não só contagens
    assert bk.execute("SELECT * FROM users ORDER BY id").fetchall() == \
        orig.execute("SELECT * FROM users ORDER BY id").fetchall()
    # /admin/status também funciona sem fetchmany/execute->cursor
    st = client.get("/admin/status", headers=auth_headers(1))
    assert st.status_code == 200 and st.get_json()["users_count"] == 5
    assert TOKEN not in st.get_data(as_text=True)


def test_chat_no_modo_turso(turso, monkeypatch):
    tabelas = {r[0] for r in _raw().execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"chats", "chat_messages"} <= tabelas

    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    sid = db.save_subject_db(uid, "Grafos", "d", 0, "i", "#f00", date.today().isoformat())

    # o libsql recusa date/datetime como parâmetro (o sqlite3 aceita, por isso o fake não pegava)
    checar = fake_libsql._check

    def checar_tipos(sql, params):
        for p in params:
            if p is not None and not isinstance(p, (int, float, str, bytes)):
                raise ValueError(f"Unsupported parameter type {p}")
        return checar(sql, params)

    monkeypatch.setattr(fake_libsql, "_check", checar_tipos)

    chat_id = db.save_chat_db(sid, uid, "Novo chat", date.today())  # date, como a rota manda
    db.save_chat_message_db(chat_id, "user", "oi")
    db.save_chat_message_db(chat_id, "assistant", "olá [1]", [{"n": 1, "file_name": "g.pdf"}])

    chat = db.get_chat_db(chat_id)
    assert chat.user_id == uid and chat.materia_nome == "Grafos"
    assert [m["papel"] for m in db.get_chat_messages_db(chat_id)] == ["user", "assistant"]
    assert db.delete_chat_db(chat_id)
