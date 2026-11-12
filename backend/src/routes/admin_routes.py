import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, send_file

from auth import require_admin
import database.database as database
import routes.document_routes as document_routes

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _db_path() -> Path:
    # app.config["DB_PATH"] (testes) tem prioridade sobre o DB_PATH do módulo
    return Path(current_app.config.get("DB_PATH") or database.DB_PATH)


@admin_bp.get("/status")
@require_admin
def status():
    """
    Estado do banco e do diretório de uploads (sem dados pessoais).
    ---
    tags:
      - Admin
    responses:
      200:
        description: db_path, db_created_at, users_count, db_size_bytes, etc.
      401:
        description: Sem token válido
      403:
        description: Usuário não é admin
    """
    db_path = _db_path()
    abs_path = db_path.resolve()
    turso = database.BACKEND == "turso"
    info = database.describe_backend()

    created_at = None
    users_count = None
    size = None
    # sqlite: só abre se o arquivo existir, para não criar um banco vazio
    if turso or abs_path.is_file():
        with database.db_connection(db_path=db_path) as conn:
            try:
                row = _consulta(conn, "SELECT value FROM meta WHERE key='db_created_at'").fetchone()
                created_at = row[0] if row else None
            except Exception:
                pass
            users_count = _consulta(conn, "SELECT COUNT(*) FROM users").fetchone()[0]
    if not turso:
        size = abs_path.stat().st_size if abs_path.is_file() else 0

    persistent = os.environ.get("STUDEX_PERSISTENT_DIR") or None
    if persistent and not turso:
        try:
            abs_path.relative_to(Path(persistent).resolve())
            under = True
        except ValueError:
            under = False
    else:
        under = None

    docs_dir = document_routes.DOCS_DIR
    pending = 0
    if docs_dir.is_dir():
        pending = sum(1 for f in docs_dir.iterdir() if f.is_file() and f.name != ".gitkeep")

    from rate_limit import client_ip_source
    return jsonify({
        "backend": info.get("backend"),
        "location": info.get("location"),
        "client_ip_source": client_ip_source(),
        "db_path": None if turso else str(abs_path),
        "db_created_at": created_at,
        "users_count": users_count,
        "db_size_bytes": size,
        "persistent_dir": persistent,
        "path_is_under_persistent_dir": under,
        "uploads_pending": pending,
    })


@admin_bp.get("/backup")
def backup():
    """
    Snapshot do banco (SQLite ou Turso) em um .db novo.
    Só existe com ADMIN_BACKUP_ENABLED=1; caso contrário 404 para todos.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Arquivo .db
      404:
        description: Backup desabilitado ou banco inexistente
    """
    # Checado antes da autenticação: desligada, a rota responde 404 até sem token.
    if os.environ.get("ADMIN_BACKUP_ENABLED") != "1":
        return jsonify({"error": "not found"}), 404
    return _backup_admin()


_CHUNK = 500


def _consulta(conn, sql, params=()):
    """cur.execute + cursor devolvido (execute() pode devolver None no libsql)."""
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _snapshot_para_sqlite(conn, destino: Path) -> None:
    """Copia esquema e linhas para um sqlite3 novo (conn.backup não existe no libsql)."""
    objetos = _consulta(
        conn,
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%'",
    ).fetchall()
    dst = sqlite3.connect(destino)
    try:
        # índices depois das linhas, para a carga ser mais rápida
        tabelas = [o for o in objetos if o[0] == "table" and o[2]]
        indices = [o for o in objetos if o[0] == "index" and o[2]]
        for _, _, ddl in tabelas:
            dst.execute(ddl)
        for _, nome, _ in tabelas:
            q = nome.replace('"', '""')
            # paginação por rowid: o cursor do libsql pode não ter fetchmany
            ultimo = 0
            while True:
                linhas = _consulta(
                    conn,
                    f'SELECT rowid, * FROM "{q}" WHERE rowid > ? ORDER BY rowid LIMIT ?',
                    (ultimo, _CHUNK),
                ).fetchall()
                if not linhas:
                    break
                ultimo = linhas[-1][0]
                marcadores = ",".join("?" * (len(linhas[0]) - 1))
                dst.executemany(
                    f'INSERT INTO "{q}" VALUES ({marcadores})',
                    [tuple(r[1:]) for r in linhas],
                )
        for _, _, ddl in indices:
            dst.execute(ddl)
        dst.commit()
    finally:
        dst.close()


@require_admin
def _backup_admin():
    db_path = _db_path()
    # turso é remoto, então só o sqlite precisa do arquivo
    if database.BACKEND != "turso" and not db_path.is_file():
        return jsonify({"error": "not found"}), 404

    tmp_dir = Path(tempfile.mkdtemp(prefix="studex-backup-"))
    tmp_file = tmp_dir / "snapshot.db"

    def _cleanup():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    try:
        # Em turso o RLock fica preso até o fim e as outras requisições esperam.
        # Escritor externo pode alterar o banco entre as páginas (snapshot não transacional).
        with database.db_connection(db_path=db_path) as conn:
            _snapshot_para_sqlite(conn, tmp_file)

        # Apaga o arquivo com o handle aberto (POSIX): nada fica em disco se o envio falhar.
        handle = open(tmp_file, "rb")
        _cleanup()

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        try:
            response = send_file(
                handle,
                mimetype="application/vnd.sqlite3",
                as_attachment=True,
                download_name=f"studex-backup-{stamp}.db",
            )
        except Exception:
            handle.close()
            raise
    except Exception:
        _cleanup()
        logger.exception("Falha ao gerar backup do banco")
        return jsonify({"error": "backup failed"}), 500

    response.headers["Cache-Control"] = "no-store"
    return response
