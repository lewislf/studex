"""Driver `libsql` FALSO para testar o modo "turso" sem rede nem o pacote real.

Instalado em sys.modules apenas pela fixture `turso_mode` (NÃO fica no PYTHONPATH).
Simula o pior caso do driver real: levanta erro em tudo que o libsql 0.1.x não
suporta ou que consideramos inseguro, para provar que o código não usa isso.
"""

import sqlite3
import threading
import time


class Unsupported(Exception):
    """Recurso não suportado/inseguro no libsql remoto."""


class _Stats:
    def __init__(self):
        self.connect_calls = []      # kwargs de cada connect()
        self.statements = []         # todo SQL executado
        self.active = 0
        self.max_active = 0
        self.commits = 0             # quantos commit() o app chamou
        self._lock = threading.Lock()

    def enter(self):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

    def leave(self):
        with self._lock:
            self.active -= 1


stats = _Stats()
db_file = None  # definido pela fixture
autocommit = False  # True simula driver que confirma cada comando na hora
expor_in_transaction = True  # False simula driver sem o atributo in_transaction


class _Cursor:
    """Cursor sem lastrowid/rowcount/fetchmany (AttributeError, como no driver
    real) e cujo execute() devolve None (a DB-API não garante devolver o cursor)."""

    def __init__(self, raw):
        object.__setattr__(self, "_raw", raw)

    def execute(self, sql, params=()):
        stats.enter()
        try:
            time.sleep(0.001)  # alarga a janela para expor concorrência indevida
            stats.statements.append(sql)
            if sql.strip().upper().startswith("PRAGMA FOREIGN_KEYS"):
                # pior caso: FK silenciosamente ignorada -> sem cascata no schema
                return None
            self._raw.execute(*_check(sql, params))
            if autocommit:
                # simula driver que confirma cada comando na hora (sem transação)
                self._raw.connection.commit()
            return None
        finally:
            stats.leave()

    def fetchone(self):
        return self._raw.fetchone()

    def fetchall(self):
        return self._raw.fetchall()

    def __getattr__(self, name):
        # lastrowid / rowcount / fetchmany / qualquer outra coisa: indisponível
        raise AttributeError(f"libsql cursor não tem {name!r}")


def _check(sql, params):
    s = sql.strip().upper()
    if s.startswith("BEGIN"):
        raise Unsupported("BEGIN explícito não é seguro no libsql remoto")
    if s.startswith("PRAGMA JOURNAL_MODE") or s.startswith("PRAGMA BUSY_TIMEOUT"):
        raise Unsupported("PRAGMA sem sentido em banco remoto")
    return sql, tuple(params)


class _Conn:
    def __init__(self, raw):
        object.__setattr__(self, "_raw", raw)

    def execute(self, sql, params=()):
        # como no sqlite3: devolve o cursor (o código do app não depende disso)
        cur = _Cursor(self._raw.cursor())
        cur.execute(sql, params)
        return cur

    def cursor(self):
        return _Cursor(self._raw.cursor())

    def commit(self):
        stats.commits += 1
        self._raw.commit()

    @property
    def in_transaction(self):
        # o sqlite3 só abre transação implícita em escrita; expor_in_transaction
        # = False simula um driver sem esse atributo (o app deve fazer commit).
        if not expor_in_transaction:
            raise AttributeError("in_transaction")
        return self._raw.in_transaction

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()

    def create_function(self, *a, **k):
        raise Unsupported("create_function não é suportado")

    def backup(self, *a, **k):
        raise Unsupported("backup")

    def executescript(self, *a, **k):
        raise Unsupported("executescript")

    def __setattr__(self, name, value):
        if name == "row_factory":
            raise Unsupported("row_factory")
        object.__setattr__(self, name, value)

    # sem __enter__/__exit__: `with conn:` levanta TypeError/AttributeError


def connect(database=None, auth_token=None, **kwargs):
    stats.connect_calls.append({"database": database, "auth_token": auth_token, **kwargs})
    raw = sqlite3.connect(db_file, check_same_thread=False)
    return _Conn(raw)
