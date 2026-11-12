#!/usr/bin/env python3
"""Teste de fumaça do driver real do Turso (libsql) para o Studex.

USO (no SEU computador, contra um banco Turso DESCARTÁVEL, nunca o de produção):

    export TURSO_DATABASE_URL="libsql://<banco-de-teste>.turso.io"
    export TURSO_AUTH_TOKEN="<token do banco de teste>"
    cd backend/src
    python ../../scripts/turso_smoke.py --i-understand-this-writes-test-data

O script escreve dados de teste (usuário, matéria, baralho, flashcard) e os
apaga ao final. Mesmo assim, use um banco separado. O token nunca é impresso.
"""

import argparse
import os
import sys
import threading
import uuid
from pathlib import Path

FLAG = "--i-understand-this-writes-test-data"
N_THREADS = 8
N_ITER = 5

_resultados: list[tuple[str, bool, str]] = []


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Teste de fumaça do Turso/libsql (escreve dados de teste!)."
    )
    p.add_argument(
        FLAG, dest="confirmado", action="store_true",
        help="confirma que o alvo é um banco Turso DESCARTÁVEL de teste",
    )
    return p.parse_args(argv)


def _mascarar(texto: str) -> str:
    """Remove o token de qualquer mensagem (defesa em profundidade)."""
    tok = os.environ.get("TURSO_AUTH_TOKEN", "")
    return texto.replace(tok, "***") if tok else texto


def check(nome: str, ok: bool, detalhe: str = "") -> bool:
    detalhe = _mascarar(detalhe)
    _resultados.append((nome, bool(ok), detalhe))
    print(f"  [{'PASS' if ok else 'FAIL'}] {nome}" + (f" - {detalhe}" if detalhe and not ok else ""))
    return bool(ok)


def _q(conn, sql, params=()):
    """cur.execute + devolve o cursor (execute() pode devolver None no libsql)."""
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


class _AbortarTeste(Exception):
    """Exceção proposital para forçar rollback no teste de atomicidade."""


MSG_ATOMICIDADE = ("o driver confirmou o comando antes do commit: NÃO faça o deploy; "
                   "exclusões podem ficar parciais")


def verificar_atomicidade(database) -> tuple[bool, str]:
    """Insere uma linha dentro de db_connection e lança exceção; a linha NÃO pode
    persistir. Se persistir, o driver faz autocommit por comando e as cascatas de
    exclusão/gravação em lote deixariam dados parciais. Devolve (ok, detalhe)."""
    chave = "smoke_atomicidade_" + uuid.uuid4().hex
    try:
        with database.db_connection() as conn:
            _q(conn, "INSERT INTO meta(key, value) VALUES(?, ?)", (chave, "x"))
            raise _AbortarTeste()
    except _AbortarTeste:
        pass
    with database.db_connection() as conn:
        n = _q(conn, "SELECT COUNT(*) FROM meta WHERE key = ?", (chave,)).fetchone()[0]
        if n:
            # limpa o resíduo antes de reportar
            _q(conn, "DELETE FROM meta WHERE key = ?", (chave,))
    if n:
        return False, MSG_ATOMICIDADE
    return True, ""


def _preparar_ambiente() -> None:
    """Valida envs e põe backend/src no sys.path (o script fica em scripts/)."""
    if not os.environ.get("TURSO_DATABASE_URL") or not os.environ.get("TURSO_AUTH_TOKEN"):
        sys.exit("Defina TURSO_DATABASE_URL e TURSO_AUTH_TOKEN (banco de TESTE).")
    # valores fictícios só para o app importar; não afetam o Turso
    os.environ.setdefault("JWT_SECRET", "smoke-test-secret-" + "x" * 32)
    os.environ.setdefault("GEMINI_API_KEY", "dummy")
    os.environ.setdefault("RATELIMIT_ENABLED", "0")
    src = Path(__file__).resolve().parent.parent / "backend" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    os.chdir(src)


def _contagens(database) -> dict[str, int]:
    with database.db_connection() as conn:
        tabelas = [r[0] for r in _q(
            conn,
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        return {t: _q(conn, f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in sorted(tabelas)}


def _executar() -> None:
    _preparar_ambiente()
    token = os.environ["TURSO_AUTH_TOKEN"]

    import database.database as database
    from main import app

    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False

    print("== Backend")
    info = database.describe_backend()
    check("backend é turso", database.BACKEND == "turso", str(info.get("backend")))
    check("describe_backend não contém o token", token not in repr(info))

    print("== init_db")
    database.init_db()
    base = _contagens(database)  # linha de base (o banco pode já ter dados)
    check("init_db criou as tabelas", "users" in base and "meta" in base, str(sorted(base)))

    print("== Atomicidade (rollback)")
    ok_at, det_at = verificar_atomicidade(database)
    check("rollback desfaz escrita (sem autocommit por comando)", ok_at, det_at)

    sufixo = uuid.uuid4().hex[:10]
    email = f"Smoke.{sufixo}@Example.com"
    senha = "senha-de-teste-12345"
    user_id = None
    client = app.test_client()
    try:
        print("== Fluxo da API")
        r = client.post("/users", json={"name": "Smoke Test", "email": email, "password": senha})
        check("POST /users -> 201", r.status_code == 201, str(r.status_code))
        user_id = (r.get_json() or {}).get("id")
        jwt_tok = (r.get_json() or {}).get("token")
        if not user_id:
            raise RuntimeError("cadastro falhou; abortando")

        r = client.post("/users", json={"name": "Dup", "email": email.lower(), "password": senha})
        check("e-mail duplicado (caixa diferente) -> 409", r.status_code == 409, str(r.status_code))

        r = client.post("/users/login", json={"email": email.lower(), "password": senha})
        check("login com e-mail em outra caixa -> 200", r.status_code == 200, str(r.status_code))
        r = client.post("/users/login", json={"email": email, "password": "errada-12345"})
        check("login com senha errada -> 401", r.status_code == 401, str(r.status_code))

        h = {"Authorization": f"Bearer {jwt_tok}"}
        base_url = f"/users/{user_id}/subjects"
        r = client.post(base_url, headers=h, json={
            "name": "Smoke Matéria", "description": "d", "domain": 0,
            "icon": "globe", "color": "#e63946", "date": "2026-01-01"})
        check("criar matéria -> 201", r.status_code == 201, str(r.status_code))
        subject_id = (r.get_json() or {}).get("id")
        r = client.post(f"{base_url}/{subject_id}/decks", headers=h, json={
            "subtitle": "Smoke Deck", "acuracy": 0, "new": 0, "learning": 0,
            "review": 0, "date": "2026-01-01T10:00:00"})
        check("criar baralho -> 201", r.status_code == 201, str(r.status_code))
        deck_id = (r.get_json() or {}).get("id")
        r = client.post(f"{base_url}/{subject_id}/decks/{deck_id}/flashcards", headers=h, json={
            "pergunta": "P?", "resposta": "R", "status": "novo",
            "creation_date": "2026-01-01T10:00:00"})
        check("criar flashcard -> 201", r.status_code == 201, str(r.status_code))
        r = client.get(f"{base_url}/{subject_id}/decks/{deck_id}/flashcards", headers=h)
        check("listar flashcards -> 200", r.status_code == 200, str(r.status_code))

        print(f"== Concorrência ({N_THREADS} threads x {N_ITER} iterações)")
        erros: list[str] = []

        def worker(i: int) -> None:
            c = app.test_client()
            try:
                for j in range(N_ITER):
                    nome = f"conc-{sufixo}-{i}-{j}"
                    rr = c.post(base_url, headers=h, json={
                        "name": nome, "description": "d", "domain": 0,
                        "icon": "x", "color": "#000", "date": "2026-01-01"})
                    if rr.status_code != 201:
                        erros.append(f"t{i} POST {rr.status_code}")
                        continue
                    sid = rr.get_json()["id"]
                    if c.get(base_url, headers=h).status_code != 200:
                        erros.append(f"t{i} GET lista")
                    if c.get(f"{base_url}/{sid}", headers=h).status_code != 200:
                        erros.append(f"t{i} GET item")
                    if c.delete(f"{base_url}/{sid}", headers=h).status_code != 204:
                        erros.append(f"t{i} DELETE")
            except Exception as e:  # noqa: BLE001
                erros.append(f"t{i} exceção {type(e).__name__}")

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(N_THREADS)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=300)
        check("threads terminaram", not any(t.is_alive() for t in ts))
        check("operações concorrentes sem erro", not erros, "; ".join(erros[:5]))
        r = client.get(base_url, headers=h)
        nomes = [s["title"] for s in (r.get_json() or [])] if r.status_code == 200 else []
        check("nenhuma matéria 'conc-' sobrou", not any(n.startswith("conc-") for n in nomes))
    except Exception as e:  # noqa: BLE001
        check("fluxo executou sem exceção", False, f"{type(e).__name__}: {e}")
    finally:
        print("== Limpeza")
        if user_id:
            try:
                r = client.delete(f"/users/{user_id}", headers={
                    "Authorization": "Bearer " + __import__("auth").create_token(user_id)})
                check("DELETE /users -> 204", r.status_code == 204, str(r.status_code))
            except Exception as e:  # noqa: BLE001
                check("DELETE /users", False, f"{type(e).__name__}: {e}")
        try:
            depois = _contagens(database)
            check("contagens de TODAS as tabelas voltaram à linha de base",
                  depois == base, f"antes={base} depois={depois}")
            with database.db_connection() as conn:
                n = _q(conn, "SELECT COUNT(*) FROM users WHERE id = ?", (user_id,)).fetchone()[0] if user_id else 0
            check("usuário de teste removido", n == 0)
        except Exception as e:  # noqa: BLE001
            check("verificação final", False, f"{type(e).__name__}: {e}")


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.confirmado:
        print(f"RECUSADO: este script ESCREVE dados de teste no Turso.\n"
              f"Use um banco DESCARTÁVEL e passe {FLAG}.", file=sys.stderr)
        return 2
    try:
        _executar()
    except Exception as exc:  # erro fora dos checks (ex.: init_db): nunca vaza o token
        _resultados.append(("execução interrompida", False,
                            _mascarar(f"{type(exc).__name__}: {exc}")))
    falhas = [r for r in _resultados if not r[1]]
    print("\n==== RESULTADO:", "PASS" if not falhas else f"FAIL ({len(falhas)} falha(s))", "====")
    for nome, _, det in falhas:
        print(f" - {nome}: {_mascarar(det)}")
    if any("atomicidade" in nome.lower() or "rollback" in nome.lower() for nome, ok, _ in _resultados if not ok):
        print("\n!!! " + MSG_ATOMICIDADE)
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
