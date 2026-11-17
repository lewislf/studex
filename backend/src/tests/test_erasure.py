"""Excluir o usuário apaga tudo dele em cascata."""

import sqlite3

from database.database import save_user_db, delete_user_db

TABELAS = ("subjects", "summaries", "decks", "flashcards", "mind_maps", "activity_days")


def test_delete_user_cascades_everywhere(temp_db):
    uid = save_user_db("Ana", "senha12345", "ana@x.com", db_path=temp_db)
    conn = sqlite3.connect(temp_db)
    conn.execute("PRAGMA foreign_keys = ON;")
    sid = conn.execute(
        "INSERT INTO subjects (user_id,name,desc,creation_date,domain,icon,color) VALUES (?,?,?,?,?,?,?)",
        (uid, "M", "d", "2026-01-01", 1, "i", "c")).lastrowid
    conn.execute("INSERT INTO summaries (subject_id,titulo,conteudo) VALUES (?,?,?)", (sid, "t", "c"))
    did = conn.execute(
        "INSERT INTO decks (subject_id,titulo,acuracia,novos,aprendendo,review) VALUES (?,?,?,?,?,?)",
        (sid, "b", 0, 1, 0, 0)).lastrowid
    conn.execute("INSERT INTO flashcards (deck_id,pergunta,resposta,status) VALUES (?,?,?,?)",
                 (did, "p", "r", "novo"))
    conn.execute("INSERT INTO mind_maps (subject_id,titulo,conteudo) VALUES (?,?,?)", (sid, "t", "c"))
    conn.execute("INSERT INTO activity_days (user_id,day) VALUES (?,?)", (uid, "2026-01-01"))
    conn.commit()
    for t in TABELAS:
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 1
    conn.close()

    assert delete_user_db(uid, db_path=temp_db) is True

    conn = sqlite3.connect(temp_db)
    for t in TABELAS + ("users",):
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0, t
    conn.close()
