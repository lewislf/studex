"""Contadores agregados (sem N+1) e commit só quando há escrita (modo turso)."""

from datetime import date

import pytest

import database.database as db
import fake_libsql
from test_turso_mode import turso  # noqa: F401  (reusa a fixture do modo turso simulado)


def _popular(db_path=db.DB_PATH):
    """Usuário com 2 matérias: A (2 resumos, 1 mapa, 2 baralhos com 3+1 cards)
    e B (vazia). Outro usuário com 1 matéria, para garantir o filtro."""
    hoje = date.today()
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com", db_path=db_path)
    outro = db.save_user_db("Bia", "senha12345", "bia@x.com", db_path=db_path)
    a = db.save_subject_db(uid, "A", "d", 1, "i", "c", hoje, db_path=db_path)
    b = db.save_subject_db(uid, "B", "d", 1, "i", "c", hoje, db_path=db_path)
    x = db.save_subject_db(outro, "X", "d", 1, "i", "c", hoje, db_path=db_path)
    for t in ("r1", "r2"):
        db.save_summary_db(a, t, "c", hoje, db_path=db_path)
    db.save_mindmap_db(a, "m1", "{}", hoje, db_path=db_path)
    d1 = db.save_deck_db(a, "d1", 0, 0, 0, 0, hoje, db_path=db_path)
    d2 = db.save_deck_db(a, "d2", 0, 0, 0, 0, hoje, db_path=db_path)
    for i in range(3):
        db.save_flashcard_db(d1, f"p{i}", "r", "novo", hoje, db_path=db_path)
    db.save_flashcard_db(d2, "p", "r", "novo", hoje, db_path=db_path)
    db.save_summary_db(x, "rx", "c", hoje, db_path=db_path)
    return uid, a, b, x


def _metodo_antigo(subject_id, db_path=db.DB_PATH):
    decks = db.get_decks_db(subject_id, db_path=db_path) or []
    return {
        "summaries": db.count_summaries_db(subject_id, db_path=db_path),
        "mind_maps": db.count_mindmaps_db(subject_id, db_path=db_path),
        "flashcards": sum(db.count_flashcards_db(d.id, db_path=db_path) for d in decks),
    }


def test_counters_iguais_ao_metodo_antigo_sqlite(temp_db):
    uid, a, b, x = _popular(temp_db)
    todos = db.get_subject_counters_db(user_id=uid, db_path=temp_db)
    assert set(todos) == {a, b}  # só as matérias do usuário
    for sid in (a, b):
        assert todos[sid] == _metodo_antigo(sid, temp_db)
    assert todos[a] == {"summaries": 2, "mind_maps": 1, "flashcards": 4}
    assert todos[b] == {"summaries": 0, "mind_maps": 0, "flashcards": 0}
    assert db.get_subject_counters_db(subject_id=x, db_path=temp_db) == {x: {"summaries": 1, "mind_maps": 0, "flashcards": 0}}
    assert db.count_user_materials_db(uid, db_path=temp_db) == (2, 1)
    with pytest.raises(ValueError):
        db.get_subject_counters_db(db_path=temp_db)


def test_counters_iguais_ao_metodo_antigo_turso(turso):
    uid, a, b, x = _popular()
    todos = db.get_subject_counters_db(user_id=uid)
    for sid in (a, b):
        assert todos[sid] == _metodo_antigo(sid)
    assert db.count_user_materials_db(uid) == (2, 1)


def test_rotas_listam_os_mesmos_contadores_turso(turso, client, auth_headers):
    # no modo turso as rotas usam a conexão compartilhada (db_path ignorado)
    uid, a, b, x = _popular()
    lista = client.get(f"/users/{uid}/subjects", headers=auth_headers(uid))
    assert lista.status_code == 200
    por_id = {s["id"]: s["counters"] for s in lista.get_json()}
    assert por_id[a] == {"summaries": 2, "mind_maps": 1, "flashcards": 4}
    assert por_id[b] == {"summaries": 0, "mind_maps": 0, "flashcards": 0}
    um = client.get(f"/users/{uid}/subjects/{a}", headers=auth_headers(uid)).get_json()
    assert um["counters"] == {"summaries": 2, "mind_maps": 1, "flashcards": 4}


def test_listagem_usa_poucas_consultas_turso(turso, client, auth_headers):
    uid, a, b, x = _popular()
    for i in range(10):  # muitas matérias: antes eram ~4 consultas por matéria
        db.save_subject_db(uid, f"extra{i}", "d", 1, "i", "c", date.today())
    antes = len(turso.stats.statements)
    assert client.get(f"/users/{uid}/subjects", headers=auth_headers(uid)).status_code == 200
    usadas = len(turso.stats.statements) - antes
    assert usadas <= 6, usadas  # auth + listar + 1 consulta agregada (+ folga)


def test_leitura_nao_faz_commit_escrita_faz_turso(turso):
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    c0 = turso.stats.commits
    assert db.user_exists_db(uid) is True          # só leitura
    db.get_subject_counters_db(user_id=uid)        # só leitura
    assert turso.stats.commits == c0
    db.save_subject_db(uid, "A", "d", 1, "i", "c", date.today())  # escrita
    assert turso.stats.commits == c0 + 1
    db.record_activity_db(uid, date.today())                      # escrita via _q
    assert turso.stats.commits == c0 + 2
    # e a escrita persistiu de verdade
    import sqlite3
    raw = sqlite3.connect(fake_libsql.db_file)
    assert raw.execute("SELECT count(*) FROM activity_days WHERE user_id=?", (uid,)).fetchone()[0] == 1


def test_sem_in_transaction_sempre_faz_commit_turso(turso, monkeypatch):
    monkeypatch.setattr(fake_libsql, "expor_in_transaction", False)
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    c0 = turso.stats.commits
    db.user_exists_db(uid)  # leitura, mas o driver não informa: commit por segurança
    assert turso.stats.commits == c0 + 1


def test_leitura_dentro_de_bloco_com_escrita_ainda_commita_turso(turso):
    uid = db.save_user_db("Ana", "senha12345", "ana@x.com")
    c0 = turso.stats.commits
    with db.db_connection() as conn:
        db._q(conn, "SELECT 1").fetchall()
        db._q(conn, "INSERT INTO activity_days (user_id, day, count) VALUES (?, ?, 1)", (uid, "2026-01-01"))
        db._q(conn, "SELECT 1").fetchall()
    assert turso.stats.commits == c0 + 1


@pytest.mark.parametrize("sql,leitura", [
    ("SELECT 1", True), ("  select x from t", True), ("PRAGMA table_info(t)", True),
    ("INSERT INTO t VALUES (1)", False), ("UPDATE t SET x=1", False), ("DELETE FROM t", False),
    ("CREATE TABLE t (x)", False), ("WITH c AS (SELECT 1) DELETE FROM t", False), ("", False),
])
def test_classificacao_de_leitura(sql, leitura):
    assert db._is_read_only(sql) is leitura
