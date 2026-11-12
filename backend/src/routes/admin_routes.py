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
    # app.config["DB_PATH"] só é definido nos testes; em produção vale o
    # DB_PATH do módulo (env STUDEX_DB_PATH ou "users.db"). Lido a cada
    # chamada para poder ser sobrescrito por monkeypatch.
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
    info = database.describe_backend()  # nunca contém o token

    created_at = None
    users_count = None
    size = None
    # No modo turso o banco é remoto: não toca no disco para o banco.
    # No modo sqlite só consulta se o arquivo existir (não cria arquivo vazio).
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
    Snapshot portátil (esquema + linhas copiados para um .db novo; funciona em
    SQLite local e em Turso) para download.
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
    # Existe para o dono poder fazer backup antes de deploys. ATENÇÃO: o
    # arquivo contém TODOS os dados pessoais (LGPD): guarde criptografado /
    # offline e apague quando não for mais necessário. Por isso fica atrás de
    # uma env explícita. A env é checada ANTES da autenticação: desligado,
    # a rota nem revela que existe (404 até sem token).
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
    """Copia esquema + linhas do banco (sqlite ou turso) para um arquivo
    sqlite3 novo. Portátil: não usa conn.backup (indisponível no libsql)."""
    objetos = _consulta(
        conn,
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%'",
    ).fetchall()
    dst = sqlite3.connect(destino)
    try:
        # tabelas primeiro, índices depois (carga mais rápida)
        tabelas = [o for o in objetos if o[0] == "table" and o[2]]
        indices = [o for o in objetos if o[0] == "index" and o[2]]
        for _, _, ddl in tabelas:
            dst.execute(ddl)
        for _, nome, _ in tabelas:
            q = nome.replace('"', '""')
            # Paginação por rowid (keyset) só com execute/fetchall: o cursor do
            # libsql pode não ter fetchmany. Todas as tabelas do schema têm rowid.
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
    # sqlite: não criar/ler arquivo inexistente; turso: banco é remoto
    if database.BACKEND != "turso" and not db_path.is_file():
        return jsonify({"error": "not found"}), 404

    # diretório temporário 0700 (mkdtemp) para o snapshot
    tmp_dir = Path(tempfile.mkdtemp(prefix="studex-backup-"))
    tmp_file = tmp_dir / "snapshot.db"

    def _cleanup():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    try:
        # um único bloco: neste processo nenhuma outra escrita acontece durante
        # o snapshot (no modo turso o RLock fica preso até o fim — as demais
        # requisições esperam; aceitável para um backup manual do admin). Um
        # escritor EXTERNO (outra instância, CLI do Turso) poderia alterar o
        # banco entre as páginas: o snapshot não é transacional nesse caso.
        with database.db_connection(db_path=db_path) as conn:
            _snapshot_para_sqlite(conn, tmp_file)

        # Abre o snapshot e já apaga diretório+arquivo: em POSIX o handle
        # aberto continua legível, então nada fica em disco mesmo que o envio
        # falhe ou a conexão caia. O werkzeug fecha o handle ao fim da resposta.
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
            handle.close()  # send_file falhou: ninguem mais fecharia o handle
            raise
    except Exception:
        _cleanup()
        logger.exception("Falha ao gerar backup do banco")
        return jsonify({"error": "backup failed"}), 500

    response.headers["Cache-Control"] = "no-store"
    return response
