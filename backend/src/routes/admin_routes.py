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

    created_at = None
    users_count = None
    if abs_path.is_file():
        # as_uri() escapa ?, # e % no caminho; modo ro não cria arquivo
        conn = sqlite3.connect(abs_path.as_uri() + "?mode=ro", uri=True)
        try:
            try:
                row = conn.execute("SELECT value FROM meta WHERE key='db_created_at'").fetchone()
                created_at = row[0] if row else None
            except sqlite3.OperationalError:
                pass
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            conn.close()

    persistent = os.environ.get("STUDEX_PERSISTENT_DIR") or None
    if persistent:
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
        "client_ip_source": client_ip_source(),
        "db_path": str(abs_path),
        "db_created_at": created_at,
        "users_count": users_count,
        "db_size_bytes": abs_path.stat().st_size if abs_path.is_file() else 0,
        "persistent_dir": persistent,
        "path_is_under_persistent_dir": under,
        "uploads_pending": pending,
    })


@admin_bp.get("/backup")
def backup():
    """
    Snapshot consistente do SQLite (API de backup do sqlite3) para download.
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


@require_admin
def _backup_admin():
    db_path = _db_path()
    # sqlite3.connect criaria um arquivo vazio em caminho inexistente
    if not db_path.is_file():
        return jsonify({"error": "not found"}), 404

    # diretório temporário 0700 (mkdtemp) para o snapshot
    tmp_dir = Path(tempfile.mkdtemp(prefix="studex-backup-"))
    tmp_file = tmp_dir / "snapshot.db"

    def _cleanup():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(tmp_file)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

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
