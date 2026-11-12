import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from urllib.parse import urlparse
from typing import Any
from pathlib import Path
import numpy as np
import logging
from datetime import date, timedelta, datetime, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from user import Usuario
from materia import Materia
from resumo import Resumo
from mapa_mental import MapaMental
from baralho import Baralho
from flashcard import Flashcard
from enums.flashcard_status import FlashcardStatus

# Lido no import porque as funções abaixo usam DB_PATH como default de argumento.
DB_PATH = Path(os.environ.get("STUDEX_DB_PATH", "users.db"))

logger = logging.getLogger(__name__)
_ph = PasswordHasher()


# sqlite3.Connection ou libsql.Connection; só se usa o subconjunto comum.
Connection = Any

# Turso se TURSO_DATABASE_URL estiver definida; senão SQLite local.
BACKEND = "turso" if os.environ.get("TURSO_DATABASE_URL", "").strip() else "sqlite"

# Modo turso: uma conexão compartilhada. O RLock fica preso durante todo o
# `with db_connection()` porque o driver libsql não faz escritas concorrentes.
_TURSO_LOCK = threading.RLock()
_turso_conn = None


def _connect_turso():
    """Abre a conexão com o Turso; libsql é importado aqui para não ser exigido no modo sqlite."""
    import libsql  # noqa: PLC0415

    conn = libsql.connect(
        database=os.environ["TURSO_DATABASE_URL"],
        auth_token=os.environ.get("TURSO_AUTH_TOKEN", ""),
    )
    # As exclusões são cascatas explícitas (delete_*_db), sem depender de FK.
    try:
        _q(conn, "PRAGMA foreign_keys = ON;")
    except Exception:
        logger.debug("Turso: PRAGMA foreign_keys não aceito (ignorado)")
    return conn


def _drop_turso_conn() -> None:
    """Descarta a conexão compartilhada; a próxima chamada reconecta."""
    global _turso_conn
    old, _turso_conn = _turso_conn, None
    if old is not None:
        try:
            old.close()
        except Exception:
            pass


def _q(conn, sql: str, params: tuple = ()):
    """Executa via cursor e o devolve; execute() pode retornar None no libsql."""
    cur = conn.cursor()
    cur.execute(sql, params)
    if not _is_read_only(sql):
        _tls.dirty = True
    return cur


def _is_read_only(sql: str) -> bool:
    """Só SELECT e PRAGMA contam como leitura; o resto é tratado como escrita."""
    primeira = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
    return primeira in ("SELECT", "PRAGMA")


# Estado de db_connection por thread (modo turso): só o bloco mais externo faz commit/rollback.
_tls = threading.local()


@contextmanager
def db_connection(db_path: Path = DB_PATH):
    """
    Conexão com o banco: commit na saída normal, rollback e re-raise em exceção.

    sqlite abre e fecha uma conexão por chamada. turso usa a conexão compartilhada
    sob RLock (db_path ignorado) e a descarta se houver erro que não seja de integridade.
    """
    if BACKEND == "turso":
        global _turso_conn
        with _TURSO_LOCK:
            if _turso_conn is None:
                _turso_conn = _connect_turso()
            conn = _turso_conn
            if getattr(_tls, "depth", 0) > 0:
                # bloco aninhado: mesma transação; só o mais externo faz commit/rollback
                yield conn
                return
            _tls.depth = 1
            _tls.dirty = False
            try:
                yield conn
                # Cada commit é uma ida à rede: pula em leitura pura, mas só se o
                # driver confirmar que não há transação aberta.
                if _tls.dirty or getattr(conn, "in_transaction", True):
                    conn.commit()
            except BaseException as exc:
                # IntegrityError não invalida a conexão; outros erros podem invalidar
                descartar = not isinstance(exc, sqlite3.IntegrityError)
                try:
                    rollback = getattr(conn, "rollback", None)
                    if rollback is not None:
                        rollback()
                    else:
                        # sem rollback não há garantia de transação desfeita
                        descartar = True
                except Exception:
                    descartar = True
                if descartar:
                    _drop_turso_conn()
                raise
            finally:
                _tls.depth = 0
                _tls.dirty = False
        return

    conn = _open_connection(db_path)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def _use_conn(conn: Connection | None, db_path: Path):
    """Usa a conexão recebida (sem commit) ou abre uma via db_connection."""
    if conn is not None:
        yield conn
    else:
        with db_connection(db_path) as own:
            yield own


def describe_backend() -> dict:
    """Backend ativo sem segredos: caminho absoluto (sqlite) ou só o host (turso)."""
    if BACKEND == "turso":
        url = os.environ.get("TURSO_DATABASE_URL", "").strip()
        if "://" not in url:
            url = "//" + url
        host = urlparse(url).hostname or ""
        return {"backend": "turso", "location": host}
    return {"backend": "sqlite", "location": str(Path(DB_PATH).resolve())}


def _email_match(lowered: str) -> tuple[str, tuple]:
    """Cláusula SQL + parâmetros do match case-insensitive de e-mail.

    py_lower é só do sqlite (o libsql não suporta create_function); no turso
    basta lower() ASCII, pois o cadastro grava e-mail em minúsculas.
    """
    if BACKEND == "turso":
        return "(email = ? OR lower(email) = ?)", (lowered, lowered)
    return "py_lower(email) = ?", (lowered,)


def _open_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Open a connection to the local SQLite database (sqlite mode only).

    Enable foreign key (i.e. a column (or group of columns) in one table that references the primary key of another table.)
    """
    conn = sqlite3.connect(db_path)
    # lower() do SQLite só trata ASCII; py_lower segue o Unicode do Python
    conn.create_function(
        "py_lower", 1, lambda v: v.lower() if isinstance(v, str) else v,
        deterministic=True,
    )
    _q(conn, "PRAGMA foreign_keys = ON;")
    # espera até 5s por lock em vez de falhar na hora
    _q(conn, "PRAGMA busy_timeout = 5000;")

    return conn

def init_db(db_path: Path = DB_PATH) -> None:
    """
    Create the database and tables if they do not exist.
    """
    if BACKEND != "turso":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with db_connection(db_path) as conn:
        if BACKEND != "turso":
            _q(conn, "PRAGMA journal_mode=WAL;")

        _q(conn,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                passwd_encrypted BLOB NOT NULL,
                gamification TEXT,
                counters TEXT
            );
            """
        )

        _q(conn,
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                desc TEXT NOT NULL,
                creation_date DATETIME,
                domain INTEGER NOT NULL,
                icon TEXT NOT NULL,
                color TEXT NOT NULL, 

                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        _q(conn,
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                conteudo TEXT NOT NULL,
                creation_date DATETIME,

                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )

        _q(conn,
            """
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                acuracia INTEGER NOT NULL,
                creation_date DATETIME,
                novos INTEGER NOT NULL,
                aprendendo INTEGER NOT NULL,
                review INTEGER NOT NULL,

                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )

        _q(conn,
            """
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                pergunta TEXT NOT NULL,
                resposta TEXT NOT NULL,
                creation_date DATETIME,

                status TEXT NOT NULL
                    CHECK(status IN ('novo', 'aprendendo', 'review', 'reaprendendo')),

                embedding TEXT,
                due_date TEXT,
                interval_days REAL DEFAULT 0,
                ease REAL DEFAULT 2.5,
                reps INTEGER DEFAULT 0,
                lapses INTEGER DEFAULT 0,

                FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
            );
            """
        )

        # Adiciona as colunas que bancos antigos não têm; consulta table_info em
        # vez de capturar "duplicate column", cuja exceção varia entre os drivers.
        existentes = {
            row[1] for row in _q(conn, "PRAGMA table_info(flashcards)").fetchall()
        }
        for coluna, definicao in (
            ("embedding", "TEXT"),
            ("due_date", "TEXT"),
            ("interval_days", "REAL DEFAULT 0"),
            ("ease", "REAL DEFAULT 2.5"),
            ("reps", "INTEGER DEFAULT 0"),
            ("lapses", "INTEGER DEFAULT 0"),
        ):
            if coluna not in existentes:
                _q(conn, f"ALTER TABLE flashcards ADD COLUMN {coluna} {definicao};")

        _q(conn,
            """
            CREATE TABLE IF NOT EXISTS mind_maps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                conteudo TEXT NOT NULL,
                creation_date DATETIME,

                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )

        # db_created_at: data da criação do banco
        _q(conn,
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);"
        )
        _q(conn,
            "INSERT OR IGNORE INTO meta(key, value) VALUES('db_created_at', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )

        _q(conn,
            """
            CREATE TABLE IF NOT EXISTS activity_days (
                user_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, day),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        created = _q(conn,
            "SELECT value FROM meta WHERE key = 'db_created_at'"
        ).fetchone()
        users_count = _q(conn, "SELECT COUNT(*) FROM users").fetchone()[0]

    # LGPD: só contagem e caminho/host no log
    if BACKEND == "turso":
        logger.info(
            "DB: backend=turso host=%s db_created_at=%s users=%s",
            describe_backend()["location"], created[0] if created else None, users_count,
        )
        return None

    abs_path = Path(db_path).resolve()
    persistent = os.environ.get("STUDEX_PERSISTENT_DIR")
    if persistent:
        try:
            abs_path.relative_to(Path(persistent).resolve())
            sob_persistente = True
        except ValueError:
            sob_persistente = False
    else:
        sob_persistente = None
    logger.info(
        "DB: path=%s db_created_at=%s users=%s under_persistent_dir=%s",
        abs_path, created[0] if created else None, users_count, sob_persistente,
    )

    return None


def save_user_db(
    name: str,
    passwd: str,
    email: str,
    gamification: dict = None,
    counters: dict = None,
    db_path: Path = DB_PATH,
) -> int | None:
    """
    Register a new user in the database.

    Returns the user_id of the new entry.
    """
    encrypted_passwd = _ph.hash(passwd)
    
    if gamification is None:
        gamification = {
            "current_streak": 0,
            "active_yesterday": False
        }
    
    if counters is None:
        counters = {
            "summaries": 0,
            "mind_maps": 0,
            "pending_flashcards_today": 0,
            "total_flashcards_created": 0
        }
    
    # Convert dicts to JSON strings
    gamification_json = json.dumps(gamification)
    counters_json = json.dumps(counters)
    
    # A coluna UNIQUE só barra e-mail idêntico; checagem e INSERT num único
    # statement tornam a unicidade case-insensitive atômica.
    cond, cond_params = _email_match(email.lower())
    sql = f"""
        INSERT INTO users (name, email, passwd_encrypted, gamification, counters)
        SELECT ?, ?, ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE {cond})
        RETURNING id
    """
    params = (name, email, encrypted_passwd, gamification_json, counters_json) + cond_params

    with db_connection(db_path) as conn:
        try:
            row = _q(conn, sql, params).fetchone()
        except sqlite3.IntegrityError:
            raise
        except Exception as exc:
            # o libsql tem classes de erro próprias; normaliza para IntegrityError
            if "unique constraint" in str(exc).lower():
                raise sqlite3.IntegrityError("email já cadastrado") from exc
            raise

        if row is None:
            raise sqlite3.IntegrityError("email já cadastrado")

        return row[0]


def get_users_db(
    name: str,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a user with the name

    Returns the list of users with the same name
    """

    with db_connection(db_path) as conn:
        rows = _q(conn, """SELECT id, name, email, passwd_encrypted, gamification, counters 
                                    FROM users 
                                    WHERE name LIKE ?""", (f"%{name}%",)).fetchall()  
        
        if rows is None:
            return None

        users = []
        for user_id, name, email, hash_passwd, gamification_json, counters_json in rows:
            gamification = json.loads(gamification_json) if gamification_json else None
            counters = json.loads(counters_json) if counters_json else None
            
            users.append(Usuario(name, email, hash_passwd, user_id, gamification, counters))
        
        return users

def user_exists_db(user_id: int, db_path: Path = DB_PATH) -> bool:
    """Consulta leve (sem desserializar JSON) usada a cada requisição autenticada."""
    with db_connection(db_path) as conn:
        return _q(conn, "SELECT 1 FROM users WHERE id = ?", (int(user_id),)).fetchone() is not None


def get_user_db(
    user_id: int,
    db_path: Path = DB_PATH,
) -> Usuario | None:
    """
    Try to search a user with id

    Returns the user, if it exists
    """

    with db_connection(db_path) as conn:
        row = _q(conn, """SELECT id, name, email, passwd_encrypted, gamification, counters 
                                    FROM users 
                                    WHERE id = ?""", (user_id,)).fetchone()  
        
        if row is None:
            return None

        user = None
        user_id, name, email, hash_passwd, gamification_json, counters_json = row
        
        gamification = json.loads(gamification_json) if gamification_json else None
        counters = json.loads(counters_json) if counters_json else None
        
        user = Usuario(name, email, hash_passwd, user_id, gamification, counters)
        
        return user


def get_user_by_email_db(
    email: str,
    db_path: Path = DB_PATH,
) -> Usuario | None:
    """
    Busca um usuário pelo email (coluna única).

    Retorna o usuário com a senha ainda criptografada em `hash_password`,
    ou None se não existir.
    """
    cond, cond_params = _email_match(email.strip().lower())

    with db_connection(db_path) as conn:
        row = _q(conn, f"""SELECT id, name, email, passwd_encrypted, gamification, counters
                                    FROM users
                                    WHERE {cond}
                                    ORDER BY (email = ?) DESC, id
                                    LIMIT 1""", cond_params + (email.strip(),)).fetchone()

        if row is None:
            return None

        user_id, name, email, hash_passwd, gamification_json, counters_json = row

        gamification = json.loads(gamification_json) if gamification_json else None
        counters = json.loads(counters_json) if counters_json else None

        return Usuario(name, email, hash_passwd, user_id, gamification, counters)


def login_user_db(
    email: str,
    passwd: str,
    db_path: Path = DB_PATH,
) -> Usuario | None:
    """
    Autentica um usuário por email + senha (argon2id).

    Retorna o usuário autenticado ou None se email/senha não conferem.
    """
    user = get_user_by_email_db(email, db_path=db_path)

    if user is None:
        return None

    try:
        _ph.verify(user.hash_password, passwd)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return None

    return user


def delete_user_db(user_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a user by user_id. (LGPD - Right to be forgotten)
    
    Returns True if a user was deleted, False if no such user_id exists.
    """
    uid = int(user_id)
    with db_connection(db_path) as conn:
        # cascata explícita, filhos primeiro: o PRAGMA foreign_keys pode ser ignorado no Turso
        _q(conn,
            """DELETE FROM flashcards WHERE deck_id IN (
                   SELECT d.id FROM decks d JOIN subjects s ON s.id = d.subject_id
                   WHERE s.user_id = ?)""", (uid,))
        _q(conn,
            "DELETE FROM decks WHERE subject_id IN (SELECT id FROM subjects WHERE user_id = ?)", (uid,))
        _q(conn,
            "DELETE FROM summaries WHERE subject_id IN (SELECT id FROM subjects WHERE user_id = ?)", (uid,))
        _q(conn,
            "DELETE FROM mind_maps WHERE subject_id IN (SELECT id FROM subjects WHERE user_id = ?)", (uid,))
        _q(conn, "DELETE FROM subjects WHERE user_id = ?", (uid,))
        _q(conn, "DELETE FROM activity_days WHERE user_id = ?", (uid,))
        # RETURNING porque rowcount não é confiável no libsql
        deleted = _q(conn, "DELETE FROM users WHERE id = ? RETURNING id", (uid,)).fetchall()
        return len(deleted) > 0


def count_people_db(db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered people in the database.
    """
    with db_connection(db_path) as conn:
        row = _q(conn, "SELECT COUNT(*) FROM users").fetchone()
        return int(row[0]) if row else 0

def print_all_people_db(db_path: Path = DB_PATH) -> None:
    """
    Prints all registered users.
    """
    with db_connection(db_path) as conn:
        rows = _q(conn, "SELECT id, name FROM users").fetchall()
        print("Registered people:")
        for user_id, name in rows:
            print(f"ID: {user_id}, Name: {name}")



### SUBJECT ###

def save_subject_db(user_id: int, name: str, desc: str, domain: int, icon: str, color: str, creation_date: date, db_path: Path = DB_PATH) -> int | None:
    """
    Register a new subject in the database. 
    
    Returns the subject_id of the new entry.
    """
    with db_connection(db_path) as conn:
        ins = """
            INSERT INTO subjects (user_id, name, desc, creation_date, domain, icon, color) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """

        # RETURNING porque lastrowid não é confiável no libsql
        return _q(conn, ins, (user_id, name, desc, creation_date, domain, icon, color)).fetchone()[0]


def get_subjects_db(
    user_id: int,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a subject with the user_id

    Returns the list of subjects with the same user_id
    """

    with db_connection(db_path) as conn:
        rows = _q(conn, """SELECT id, user_id, name, desc, creation_date, domain, icon, color 
                                    FROM subjects 
                                    WHERE user_id = ?
                                    ORDER BY creation_date DESC""", (user_id,)).fetchall()  
        
        if rows is None:
            return None

        subjects = []
        for subject_id, user_id, name, desc, creation_date, domain, icon, color in rows:
            subjects.append(Materia(user_id, name, desc, domain, icon, color, creation_date, subject_id))
        
        return subjects

def get_subject_db(
    subject_id: int,
    db_path: Path = DB_PATH,
) -> Materia | None:
    """
    Try to search a subject with id

    Returns the subject, if it exists
    """

    with db_connection(db_path) as conn:
        row = _q(conn, """SELECT id, user_id, name, desc, creation_date, domain, icon, color 
                                    FROM subjects 
                                    WHERE id = ?""", (subject_id,)).fetchone()  
        
        if row is None:
            return None

        subject = None
        subject_id, user_id, name, desc, creation_date, domain, icon, color = row
        subject = Materia(user_id, name, desc, domain, icon, color, creation_date, subject_id)
        
        return subject


def delete_subject_db(subject_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a subject by subject_id. (LGPD - Right to be forgotten)
    
    Returns True if a subject was deleted, False if no such subject_id exists.
    """
    sid = int(subject_id)
    with db_connection(db_path) as conn:
        # cascata explícita, filhos primeiro (ver delete_user_db)
        _q(conn,
            "DELETE FROM flashcards WHERE deck_id IN (SELECT id FROM decks WHERE subject_id = ?)", (sid,))
        _q(conn, "DELETE FROM decks WHERE subject_id = ?", (sid,))
        _q(conn, "DELETE FROM summaries WHERE subject_id = ?", (sid,))
        _q(conn, "DELETE FROM mind_maps WHERE subject_id = ?", (sid,))
        deleted = _q(conn, "DELETE FROM subjects WHERE id = ? RETURNING id", (sid,)).fetchall()
        return len(deleted) > 0

def count_subjects_db(user_id: int, db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered subjects in the database with given user_id.
    """
    with db_connection(db_path) as conn:
        row = _q(conn, "SELECT COUNT(*) FROM subjects WHERE user_id = ?", (user_id,),).fetchone()
        return int(row[0]) if row else 0


### SUMMARY ###

def save_summary_db(subject_id: int, titulo: str, conteudo: str, creation_date: date, db_path: Path = DB_PATH, conn: Connection | None = None) -> int | None:
    """
    Register a new summary in the database. 
    
    Returns the summary_id of the new entry.
    """
    with _use_conn(conn, db_path) as conn:
        cur = conn.cursor()

        ins = """
            INSERT INTO summaries (subject_id, titulo, conteudo, creation_date) 
            VALUES (?, ?, ?, ?)RETURNING id
        """

        # RETURNING porque lastrowid não é confiável no libsql
        cur.execute(ins, (subject_id, titulo, conteudo, creation_date))
        return cur.fetchone()[0]


def get_summaries_db(
    subject_id: int,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a summary with the name

    Returns the list of summarys with the same name
    """

    with db_connection(db_path) as conn:
        rows = _q(conn, """SELECT id, subject_id, titulo, conteudo, creation_date
                                    FROM summaries 
                                    WHERE subject_id = ?""", (subject_id,)).fetchall()  
        
        if rows is None:
            return None

        summaries = []
        for summary_id, subject_id, titulo, conteudo, creation_date in rows:
            summaries.append(Resumo(subject_id, titulo, conteudo, creation_date, summary_id))
        
        return summaries

def get_summary_db(
    summary_id: int,
    db_path: Path = DB_PATH,
) -> Resumo | None:
    """
    Try to search a summary with id

    Returns the summary, if it exists
    """

    with db_connection(db_path) as conn:
        row = _q(conn, """SELECT id, subject_id, titulo, conteudo, creation_date
                                    FROM summaries 
                                    WHERE id = ?""", (summary_id,)).fetchone()  
        
        if row is None:
            return None

        summary = None
        summary_id, subject_id, titulo, conteudo, creation_date = row
        summary = Resumo(subject_id, titulo, conteudo, creation_date, summary_id)
        
        return summary


def delete_summary_db(summary_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a summary by summary_id. (LGPD - Right to be forgotten)
    
    Returns True if a summary was deleted, False if no such summary_id exists.
    """
    with db_connection(db_path) as conn:
        deleted = _q(conn,
            "DELETE FROM summaries WHERE id = ? RETURNING id", (int(summary_id),)
        ).fetchall()
        return len(deleted) > 0

def count_summaries_db(subject_id: int, db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered summaries in the database with given subject_id.
    """
    with db_connection(db_path) as conn:
        row = _q(conn, "SELECT COUNT(*) FROM summaries WHERE subject_id = ?", (subject_id,),).fetchone()
        return int(row[0]) if row else 0

### MIND MAP ###

def save_mindmap_db(subject_id: int, titulo: str, conteudo: str, creation_date: date, db_path: Path = DB_PATH, conn: Connection | None = None) -> int | None:
    """
    Register a new mind map in the database.

    `conteudo` is expected to be a JSON string (nodes/edges).

    Returns the mind_map_id of the new entry.
    """
    with _use_conn(conn, db_path) as conn:
        cur = conn.cursor()

        ins = """
            INSERT INTO mind_maps (subject_id, titulo, conteudo, creation_date)
            VALUES (?, ?, ?, ?)RETURNING id
        """

        # RETURNING porque lastrowid não é confiável no libsql
        cur.execute(ins, (subject_id, titulo, conteudo, creation_date))
        return cur.fetchone()[0]


def get_mindmaps_db(
    subject_id: int,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a mind map with the name

    Returns the list of mind maps with the same name
    """

    with db_connection(db_path) as conn:
        rows = _q(conn, """SELECT id, subject_id, titulo, conteudo, creation_date
                                    FROM mind_maps
                                    WHERE subject_id = ?""", (subject_id,)).fetchall()

        if rows is None:
            return None

        mind_maps = []
        for mind_map_id, subject_id, titulo, conteudo, creation_date in rows:
            mind_maps.append(MapaMental(subject_id, titulo, conteudo, creation_date, mind_map_id))

        return mind_maps


def get_mindmap_db(
    mind_map_id: int,
    db_path: Path = DB_PATH,
) -> MapaMental | None:
    """
    Try to search a mind map with id

    Returns the mind map, if it exists
    """

    with db_connection(db_path) as conn:
        row = _q(conn, """SELECT id, subject_id, titulo, conteudo, creation_date
                                    FROM mind_maps
                                    WHERE id = ?""", (mind_map_id,)).fetchone()

        if row is None:
            return None

        mind_map_id, subject_id, titulo, conteudo, creation_date = row
        return MapaMental(subject_id, titulo, conteudo, creation_date, mind_map_id)


def delete_mindmap_db(mind_map_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a mind map by mind_map_id.

    Returns True if a mind map was deleted, False if no such mind_map_id exists.
    """
    with db_connection(db_path) as conn:
        deleted = _q(conn,
            "DELETE FROM mind_maps WHERE id = ? RETURNING id", (int(mind_map_id),)
        ).fetchall()
        return len(deleted) > 0


def count_mindmaps_db(subject_id: int, db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered mind maps in the database with given subject_id.
    """
    with db_connection(db_path) as conn:
        row = _q(conn, "SELECT COUNT(*) FROM mind_maps WHERE subject_id = ?", (subject_id,),).fetchone()
        return int(row[0]) if row else 0


### DECK ###

def save_deck_db(subject_id: int, titulo: str, acuracia: int, novos: int, aprendendo: int, review: int, creation_date: date, db_path: Path = DB_PATH, conn: Connection | None = None) -> int | None:
    """
    Register a new deck in the database. 
    
    Returns the deck_id of the new entry.
    """
    with _use_conn(conn, db_path) as conn:
        cur = conn.cursor()

        ins = """
            INSERT INTO decks (subject_id, titulo, acuracia, novos, aprendendo, review, creation_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)RETURNING id
        """

        # RETURNING porque lastrowid não é confiável no libsql
        cur.execute(ins, (subject_id, titulo, acuracia, novos, aprendendo, review, creation_date))
        return cur.fetchone()[0]


def get_decks_db(
    subject_id: int,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a deck with the subject id

    Returns the list of decks with the same subject id
    """

    with db_connection(db_path) as conn:
        rows = _q(conn, """SELECT id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date
                                    FROM decks 
                                    WHERE subject_id LIKE ?""", (subject_id,)).fetchall()  
        
        if rows is None:
            return None

        decks = []
        for deck_id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date in rows:
            decks.append(Baralho(subject_id, titulo, acuracia, novos, aprendendo, review, creation_date, deck_id))
        
        return decks

def get_deck_db(
    deck_id: int,
    db_path: Path = DB_PATH,
) -> Resumo | None:
    """
    Try to search a deck with id

    Returns the deck, if it exists
    """

    with db_connection(db_path) as conn:
        row = _q(conn, """SELECT id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date
                                    FROM decks 
                                    WHERE id = ?""", (deck_id,)).fetchone()  
        
        if row is None:
            return None

        deck = None
        deck_id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date = row
        deck = Baralho(subject_id, titulo, acuracia, novos, aprendendo, review, creation_date, deck_id)
        
        return deck


def delete_deck_db(deck_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a deck by deck_id. (LGPD - Right to be forgotten)
    
    Returns True if a deck was deleted, False if no such deck_id exists.
    """
    did = int(deck_id)
    with db_connection(db_path) as conn:
        # cascata explícita, filhos primeiro (ver delete_user_db)
        _q(conn, "DELETE FROM flashcards WHERE deck_id = ?", (did,))
        deleted = _q(conn, "DELETE FROM decks WHERE id = ? RETURNING id", (did,)).fetchall()
        return len(deleted) > 0

def count_deck_db(subject_id: int, db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered deck in the database with given subject_id.
    """
    with db_connection(db_path) as conn:
        row = _q(conn, "SELECT COUNT(*) FROM decks WHERE subject_id = ?", (subject_id,),).fetchone()
        return int(row[0]) if row else 0


### FLASHCARDS ###

def save_flashcard_db(
    deck_id: int | None,
    pergunta: str,
    resposta: str,
    status: str,
    creation_date: date,
    db_path: Path = DB_PATH,
    conn: Connection | None = None,
    embedding: list[float] | None = None,
) -> int | None:
    """
    Register a new flashcard in the database.

    `embedding` (se já calculado pelo dedup) é gravado junto, evitando
    recálculo depois.

    Returns the flashcard_id of the new entry.
    """

    with _use_conn(conn, db_path) as conn:
        cur = conn.cursor()

        embedding_json = json.dumps(embedding) if embedding is not None else None

        cur.execute(
            """
            INSERT INTO flashcards (
                deck_id,
                pergunta,
                resposta,
                status,
                creation_date,
                embedding
            )
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                deck_id,
                pergunta,
                resposta,
                status,
                creation_date,
                embedding_json,
            ),
        )

        return cur.fetchone()[0]

def get_flashcard_db(
    flashcard_id: int,
    db_path: Path = DB_PATH,
) -> Flashcard | None:
    """
    Search a flashcard by id.
    """

    with db_connection(db_path) as conn:
        row = _q(conn,
            """
            SELECT
                id,
                deck_id,
                pergunta,
                resposta,
                status,
                creation_date,
                embedding,
                due_date,
                interval_days,
                ease,
                reps,
                lapses
            FROM flashcards
            WHERE id = ?
            """,
            (flashcard_id,),
        ).fetchone()

        if row is None:
            return None

        (
            flashcard_id,
            deck_id,
            pergunta,
            resposta,
            status,
            creation_date,
            embedding_json,
            due_date,
            interval_days,
            ease,
            reps,
            lapses,
        ) = row

        return Flashcard(
            deck_id,
            pergunta,
            resposta,
            status,
            creation_date,
            flashcard_id,
            embedding=json.loads(embedding_json) if embedding_json else None,
            due_date=due_date,
            interval_days=interval_days if interval_days is not None else 0,
            ease=ease if ease is not None else 2.5,
            reps=reps if reps is not None else 0,
            lapses=lapses if lapses is not None else 0,
        )

def get_flashcards_db(
    deck_id: int,
    db_path: Path = DB_PATH,
) -> list[Flashcard]:
    """
    Returns all flashcards from a deck.
    """

    with db_connection(db_path) as conn:
        rows = _q(conn,
            """
            SELECT
                id,
                deck_id,
                pergunta,
                resposta,
                status,
                creation_date,
                embedding,
                due_date,
                interval_days,
                ease,
                reps,
                lapses
            FROM flashcards
            WHERE deck_id = ?
            """,
            (deck_id,),
        ).fetchall()

        flashcards = []

        for (
            flashcard_id,
            deck_id,
            pergunta,
            resposta,
            status,
            creation_date,
            embedding_json,
            due_date,
            interval_days,
            ease,
            reps,
            lapses,
        ) in rows:

            flashcards.append(
                Flashcard(
                    deck_id,
                    pergunta,
                    resposta,
                    status,
                    creation_date,
                    flashcard_id,
                    embedding=json.loads(embedding_json) if embedding_json else None,
                    due_date=due_date,
                    interval_days=interval_days if interval_days is not None else 0,
                    ease=ease if ease is not None else 2.5,
                    reps=reps if reps is not None else 0,
                    lapses=lapses if lapses is not None else 0,
                )
            )

        return flashcards


def get_flashcards_by_subject_db(
    subject_id: int,
    db_path: Path = DB_PATH,
) -> list[Flashcard]:
    """
    Returns all flashcards from every deck of a subject (join com decks).

    Usado pelo dedup semântico: compara os cards novos contra todos os cards
    já existentes na matéria, não só os do baralho sendo criado.
    """

    with db_connection(db_path) as conn:
        rows = _q(conn,
            """
            SELECT
                f.id,
                f.deck_id,
                f.pergunta,
                f.resposta,
                f.status,
                f.creation_date,
                f.embedding
            FROM flashcards f
            JOIN decks d ON d.id = f.deck_id
            WHERE d.subject_id = ?
            """,
            (subject_id,),
        ).fetchall()

        flashcards = []

        for flashcard_id, deck_id, pergunta, resposta, status, creation_date, embedding_json in rows:

            flashcards.append(
                Flashcard(
                    deck_id,
                    pergunta,
                    resposta,
                    status,
                    creation_date,
                    flashcard_id,
                    embedding=json.loads(embedding_json) if embedding_json else None,
                )
            )

        return flashcards


def update_flashcard_embedding_db(
    flashcard_id: int,
    embedding: list[float],
    db_path: Path = DB_PATH,
    conn: Connection | None = None,
) -> None:
    """
    Grava o embedding de um flashcard já existente (migração preguiçosa:
    calculado na primeira vez que o dedup semântico o encontra sem embedding).
    """

    with _use_conn(conn, db_path) as conn:
        cur = conn.cursor()

        cur.execute(
            "UPDATE flashcards SET embedding = ? WHERE id = ?",
            (json.dumps(embedding), flashcard_id),
        )


def delete_flashcard_db(
    flashcard_id: int,
    db_path: Path = DB_PATH,
) -> bool:
    """
    Delete a flashcard.

    Returns True if deleted.
    """

    with db_connection(db_path) as conn:
        deleted = _q(conn,
            "DELETE FROM flashcards WHERE id = ? RETURNING id", (flashcard_id,)
        ).fetchall()
        return len(deleted) > 0

def count_flashcards_db(
    deck_id: int,
    db_path: Path = DB_PATH,
) -> int:
    """
    Returns the total number of flashcards in a deck.
    """

    with db_connection(db_path) as conn:
        row = _q(conn,
            """
            SELECT COUNT(*)
            FROM flashcards
            WHERE deck_id = ?
            """,
            (deck_id,),
        ).fetchone()

        return int(row[0]) if row else 0


def count_due_flashcards_db(
    user_id: int,
    today: date | None = None,
    db_path: Path = DB_PATH,
) -> int:
    """
    Conta os flashcards pendentes de revisão hoje em todos os baralhos do
    usuário: cards novos + cards vencidos (due_date <= hoje). Mesma definição
    da fila de estudo (get_user_study_queue_db), sem o limite.
    """
    if today is None:
        today = date.today()

    today_iso = today.isoformat() if isinstance(today, date) else str(today)

    with db_connection(db_path) as conn:
        row = _q(conn,
            """
            SELECT COUNT(*)
            FROM flashcards f
            JOIN decks d ON d.id = f.deck_id
            JOIN subjects s ON s.id = d.subject_id
            WHERE s.user_id = ?
              AND (
                f.status = 'novo'
                OR (f.status != 'novo' AND f.due_date IS NOT NULL AND f.due_date <= ?)
              )
            """,
            (user_id, today_iso),
        ).fetchone()

        return int(row[0]) if row else 0


def get_subject_counters_db(
    user_id: int | None = None,
    subject_id: int | None = None,
    db_path: Path = DB_PATH,
) -> dict[int, dict[str, int]]:
    """
    Contadores (resumos, mapas mentais, flashcards) por matéria, numa única consulta.

    Filtra por user_id (todas as matérias do usuário) ou por subject_id (uma).
    Retorna {subject_id: {"summaries": n, "mind_maps": n, "flashcards": n}}.
    """
    if user_id is None and subject_id is None:
        raise ValueError("informe user_id ou subject_id")
    campo, valor = ("s.user_id", user_id) if subject_id is None else ("s.id", subject_id)
    with db_connection(db_path) as conn:
        rows = _q(conn,
            f"""
            SELECT s.id,
                   (SELECT COUNT(*) FROM summaries su WHERE su.subject_id = s.id),
                   (SELECT COUNT(*) FROM mind_maps m WHERE m.subject_id = s.id),
                   (SELECT COUNT(*) FROM flashcards f
                      JOIN decks d ON d.id = f.deck_id
                     WHERE d.subject_id = s.id)
            FROM subjects s
            WHERE {campo} = ?
            """,
            (valor,),
        ).fetchall()
    return {
        int(r[0]): {"summaries": int(r[1]), "mind_maps": int(r[2]), "flashcards": int(r[3])}
        for r in rows
    }


def count_user_materials_db(user_id: int, db_path: Path = DB_PATH) -> tuple[int, int]:
    """(total de resumos, total de mapas mentais) de todas as matérias do usuário."""
    with db_connection(db_path) as conn:
        row = _q(conn,
            """
            SELECT
              (SELECT COUNT(*) FROM summaries su JOIN subjects s ON s.id = su.subject_id WHERE s.user_id = ?),
              (SELECT COUNT(*) FROM mind_maps m JOIN subjects s ON s.id = m.subject_id WHERE s.user_id = ?)
            """,
            (user_id, user_id),
        ).fetchone()
    return (int(row[0]), int(row[1])) if row else (0, 0)


def count_flashcards_by_user_db(
    user_id: int,
    db_path: Path = DB_PATH,
) -> int:
    """
    Conta o total de flashcards criados em todos os baralhos do usuário.
    """
    with db_connection(db_path) as conn:
        row = _q(conn,
            """
            SELECT COUNT(*)
            FROM flashcards f
            JOIN decks d ON d.id = f.deck_id
            JOIN subjects s ON s.id = d.subject_id
            WHERE s.user_id = ?
            """,
            (user_id,),
        ).fetchone()

        return int(row[0]) if row else 0


def update_flashcard_review_db(
    flashcard_id: int,
    status: str,
    due_date: str,
    interval_days: float,
    ease: float,
    reps: int,
    lapses: int,
    db_path: Path = DB_PATH,
    conn: Connection | None = None,
) -> None:
    """
    Grava o resultado de uma revisão SRS (srs.apply_review) num flashcard.
    """

    with _use_conn(conn, db_path) as conn:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE flashcards
            SET status = ?, due_date = ?, interval_days = ?, ease = ?, reps = ?, lapses = ?
            WHERE id = ?
            """,
            (status, due_date, interval_days, ease, reps, lapses, flashcard_id),
        )



def get_study_queue_db(
    deck_id: int,
    limit: int = 20,
    today: date | None = None,
    db_path: Path = DB_PATH,
) -> list[Flashcard]:
    """
    Monta a fila de estudo de um baralho: primeiro os cards vencidos
    (due_date <= hoje e status != 'novo', mais atrasados primeiro), depois
    os cards novos (status 'novo', mais antigos primeiro). Limitado a
    `limit` cards no total.
    """
    if today is None:
        today = date.today()

    today_iso = today.isoformat() if isinstance(today, date) else str(today)

    with db_connection(db_path) as conn:
        rows = _q(conn,
            """
            SELECT
                id, deck_id, pergunta, resposta, status, creation_date,
                embedding, due_date, interval_days, ease, reps, lapses
            FROM flashcards
            WHERE deck_id = ? AND status != 'novo' AND due_date IS NOT NULL AND due_date <= ?
            ORDER BY due_date ASC
            """,
            (deck_id, today_iso),
        ).fetchall()

        remaining = max(0, limit - len(rows))

        if remaining > 0:
            rows += _q(conn,
                """
                SELECT
                    id, deck_id, pergunta, resposta, status, creation_date,
                    embedding, due_date, interval_days, ease, reps, lapses
                FROM flashcards
                WHERE deck_id = ? AND status = 'novo'
                ORDER BY creation_date ASC, id ASC
                LIMIT ?
                """,
                (deck_id, remaining),
            ).fetchall()

        flashcards = []

        for (
            flashcard_id,
            fdeck_id,
            pergunta,
            resposta,
            status,
            creation_date,
            embedding_json,
            due_date,
            interval_days,
            ease,
            reps,
            lapses,
        ) in rows[:limit]:

            flashcards.append(
                Flashcard(
                    fdeck_id,
                    pergunta,
                    resposta,
                    status,
                    creation_date,
                    flashcard_id,
                    embedding=json.loads(embedding_json) if embedding_json else None,
                    due_date=due_date,
                    interval_days=interval_days if interval_days is not None else 0,
                    ease=ease if ease is not None else 2.5,
                    reps=reps if reps is not None else 0,
                    lapses=lapses if lapses is not None else 0,
                )
            )

        return flashcards


def get_user_study_queue_db(
    user_id: int,
    limit: int = 20,
    today: date | None = None,
    db_path: Path = DB_PATH,
) -> list[tuple[Flashcard, int, str, int, str]]:
    """
    Monta a fila de estudo global de um usuário: cards de todos os baralhos
    de todas as matérias, na mesma ordenação da fila por baralho (vencidos
    primeiro, mais atrasados antes; depois novos mais antigos). Limitado a
    `limit` cards no total.

    Returns
    -------
    list[tuple[Flashcard, int, str, int, str]]
        Cada item é (flashcard, deck_id, deck_titulo, subject_id, subject_name).
    """
    if today is None:
        today = date.today()

    today_iso = today.isoformat() if isinstance(today, date) else str(today)

    with db_connection(db_path) as conn:
        rows = _q(conn,
            """
            SELECT
                f.id, f.deck_id, f.pergunta, f.resposta, f.status, f.creation_date,
                f.embedding, f.due_date, f.interval_days, f.ease, f.reps, f.lapses,
                d.titulo, s.id, s.name
            FROM flashcards f
            JOIN decks d ON d.id = f.deck_id
            JOIN subjects s ON s.id = d.subject_id
            WHERE s.user_id = ? AND f.status != 'novo' AND f.due_date IS NOT NULL AND f.due_date <= ?
            ORDER BY f.due_date ASC
            """,
            (user_id, today_iso),
        ).fetchall()

        remaining = max(0, limit - len(rows))

        if remaining > 0:
            rows += _q(conn,
                """
                SELECT
                    f.id, f.deck_id, f.pergunta, f.resposta, f.status, f.creation_date,
                    f.embedding, f.due_date, f.interval_days, f.ease, f.reps, f.lapses,
                    d.titulo, s.id, s.name
                FROM flashcards f
                JOIN decks d ON d.id = f.deck_id
                JOIN subjects s ON s.id = d.subject_id
                WHERE s.user_id = ? AND f.status = 'novo'
                ORDER BY f.creation_date ASC, f.id ASC
                LIMIT ?
                """,
                (user_id, remaining),
            ).fetchall()

        result = []

        for (
            flashcard_id,
            fdeck_id,
            pergunta,
            resposta,
            status,
            creation_date,
            embedding_json,
            due_date,
            interval_days,
            ease,
            reps,
            lapses,
            deck_titulo,
            subject_id,
            subject_name,
        ) in rows[:limit]:

            flashcard = Flashcard(
                fdeck_id,
                pergunta,
                resposta,
                status,
                creation_date,
                flashcard_id,
                embedding=json.loads(embedding_json) if embedding_json else None,
                due_date=due_date,
                interval_days=interval_days if interval_days is not None else 0,
                ease=ease if ease is not None else 2.5,
                reps=reps if reps is not None else 0,
                lapses=lapses if lapses is not None else 0,
            )

            result.append((flashcard, fdeck_id, deck_titulo, subject_id, subject_name))

        return result


def refresh_deck_counters_db(
    deck_id: int,
    db_path: Path = DB_PATH,
    conn: Connection | None = None,
) -> None:
    """
    Recalcula decks.novos/aprendendo/review a partir dos status reais dos
    flashcards do baralho ('reaprendendo' conta como aprendendo) e atualiza
    a linha do deck.
    """

    with _use_conn(conn, db_path) as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT status, COUNT(*) FROM flashcards WHERE deck_id = ? GROUP BY status",
            (deck_id,),
        )
        rows = cur.fetchall()

        counts = {"novo": 0, "aprendendo": 0, "review": 0}
        for status, count in rows:
            if status == "novo":
                counts["novo"] += count
            elif status == "review":
                counts["review"] += count
            else:
                # aprendendo e reaprendendo contam juntos
                counts["aprendendo"] += count

        cur.execute(
            "UPDATE decks SET novos = ?, aprendendo = ?, review = ? WHERE id = ?",
            (counts["novo"], counts["aprendendo"], counts["review"], deck_id),
        )



### MATERIALS ###


def save_materials_db(
    subject_id: int,
    materials: list[dict],
    db_path: Path = DB_PATH,
) -> None:
    """
    Saves all materials returned by the LLM.

    Parameters
    ----------
    subject_id : int
        Subject to which the materials belong.

    materials : list[dict]
        Output produced by the LLM.
    """

    # numa única transação: se algo falhar, nada é salvo
    with db_connection(db_path) as conn:

        for material in materials:

            tipo = material["tipo"]

            if tipo == "resumo":

                save_summary_db(
                    subject_id=subject_id,
                    titulo=material["titulo"],
                    conteudo=json.dumps(material["conteudo"], ensure_ascii=False),
                    creation_date=material["creation_date"],
                    db_path=db_path,
                    conn=conn
                )

            elif tipo == "mapa_mental":

                save_mindmap_db(
                    subject_id=subject_id,
                    titulo=material["titulo"],
                    conteudo=json.dumps(material["conteudo"], ensure_ascii=False),
                    creation_date=material["creation_date"],
                    db_path=db_path,
                    conn=conn
                )

            elif tipo == "baralho":

                deck_id = save_deck_db(
                    subject_id=subject_id,
                    titulo=material["titulo"],
                    acuracia=0,
                    novos=len(material["conteudo"]["flashcards"]),
                    aprendendo=0,
                    review=0,
                    creation_date=material["creation_date"],
                    db_path=db_path,
                    conn=conn
                )

                for flashcard in material["conteudo"]["flashcards"]:

                    save_flashcard_db(
                        deck_id=deck_id,
                        pergunta=flashcard["pergunta"],
                        resposta=flashcard["resposta"],
                        status=FlashcardStatus.NOVO.value,
                        creation_date=material["creation_date"],
                        db_path=db_path,
                        conn=conn,
                        # embedding já calculado pelo dedup (rag_api/dedup.py),
                        # não recalcula aqui
                        embedding=flashcard.get("embedding"),
                    )

            else:
                raise ValueError(f"Unknown material type: {tipo}")


def match_subject_user_db(subject_id:int, user_id:int, db_path: Path = DB_PATH):
    with db_connection(db_path) as conn:
        row = _q(conn, """SELECT user_id
                                    FROM subjects
                                    WHERE id = ?""", (subject_id,)).fetchone()

        if row is None:
            return False

        return row[0] == user_id


### ACTIVITY (streak/heatmap) ###

def record_activity_db(
    user_id: int,
    day: str,
    db_path: Path = DB_PATH,
    conn: Connection | None = None,
) -> None:
    """
    Registra 1 atividade do usuário no dia (revisão de flashcard ou envio de
    arquivo). Incrementa o contador se o dia já existir.

    Nunca levanta exceção: um erro aqui não pode derrubar a rota chamadora.
    """
    try:
        with _use_conn(conn, db_path) as conn_:
            _q(conn_,
                """
                INSERT INTO activity_days (user_id, day, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, day) DO UPDATE SET count = count + 1
                """,
                (user_id, day),
            )
    except Exception:
        logger.exception("Falha ao registrar atividade do usuário %s no dia %s", user_id, day)


def get_activity_days_db(
    user_id: int,
    since_day: str,
    db_path: Path = DB_PATH,
) -> dict:
    """
    Retorna {day: count} com todos os dias de atividade do usuário a partir
    de `since_day` (inclusive).
    """
    with db_connection(db_path) as conn:
        rows = _q(conn,
            """
            SELECT day, count
            FROM activity_days
            WHERE user_id = ? AND day >= ?
            ORDER BY day ASC
            """,
            (user_id, since_day),
        ).fetchall()

        return {day: count for day, count in rows}


def compute_streak(days_set: set[str], today: date) -> int:
    """
    Calcula a ofensiva (streak) de dias consecutivos ativos terminando hoje.

    Se hoje ainda não está em `days_set`, o streak não zera antes do dia
    acabar: conta os dias consecutivos terminando ontem.
    """
    today_iso = today.isoformat()

    if today_iso in days_set:
        cursor = today
    else:
        cursor = today - timedelta(days=1)

        if cursor.isoformat() not in days_set:
            return 0

    streak = 0
    while cursor.isoformat() in days_set:
        streak += 1
        cursor -= timedelta(days=1)

    return streak