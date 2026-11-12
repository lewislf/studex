"""
Rate limiting em memória (janela deslizante).

O estado vive no processo: só vale com 1 worker (gunicorn 1 worker + 8 threads);
com mais workers ou instâncias o limite efetivo multiplica.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque

from flask import current_app, jsonify, request

_MAX_KEYS = 50_000  # teto de chaves em memória

# Chave só deste processo: IP e e-mail não ficam em claro na memória.
_MAC_KEY = secrets.token_bytes(32)


def mac_key(kind: str, *parts: str) -> str:
    """Chave opaca (HMAC-SHA256) para IP/e-mail; e-mail é normalizado antes."""
    data = "\0".join(parts).encode("utf-8")
    return kind + ":" + hmac.new(_MAC_KEY, data, hashlib.sha256).hexdigest()


def normalise_email(email: str) -> str:
    return email.strip().lower()


class SlidingWindowLimiter:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        # chave -> [janela_em_segundos, deque de timestamps]
        self._hits: dict[str, list] = {}
        self._ops = 0

    def _prune(self, key: str, now: float) -> deque | None:
        entry = self._hits.get(key)
        if entry is None:
            return None
        window, dq = entry
        while dq and now - dq[0] >= window:
            dq.popleft()
        if not dq:
            del self._hits[key]
            return None
        return dq

    def _sweep(self, now: float) -> None:
        self._ops += 1
        if self._ops % 500 and len(self._hits) < _MAX_KEYS:
            return
        for k in list(self._hits):
            self._prune(k, now)
        if len(self._hits) >= _MAX_KEYS:
            # descarta as mais antigas em vez de clear(), para não liberar quem está bloqueado
            ordered = sorted(self._hits, key=lambda k: self._hits[k][1][-1])
            for k in ordered[: len(self._hits) - int(_MAX_KEYS * 0.9)]:
                del self._hits[k]

    def _wait(self, key: str, limit: int, now: float) -> int:
        dq = self._prune(key, now)
        if dq is None or len(dq) < limit:
            return 0
        window = self._hits[key][0]
        return max(1, int(window - (now - dq[0])) + 1)

    def _add(self, key: str, window: float, now: float) -> None:
        self._sweep(now)
        self._prune(key, now)
        entry = self._hits.setdefault(key, [window, deque()])
        entry[0] = window
        entry[1].append(now)

    def retry_after(self, key: str, limit: int, window: float) -> int:
        """Segundos até liberar (0 = liberado). Não registra tentativa."""
        with self._lock:
            return self._wait(key, limit, self._clock())

    def check_many(self, checks) -> int:
        """checks = [(key, limit)]. Maior espera entre elas (0 = liberado), sob um lock."""
        with self._lock:
            now = self._clock()
            return max([self._wait(k, lim, now) for k, lim in checks] + [0])

    def record(self, key: str, window: float) -> None:
        with self._lock:
            self._add(key, window, self._clock())

    def record_many(self, items) -> None:
        """items = [(key, window)] registrados sob um único lock."""
        with self._lock:
            now = self._clock()
            for k, w in items:
                self._add(k, w, now)

    def check_and_record(self, key: str, limit: int, window: float) -> int:
        """Atômico: se há vaga registra e devolve 0; senão devolve a espera."""
        with self._lock:
            now = self._clock()
            wait = self._wait(key, limit, now)
            if wait:
                return wait
            self._add(key, window, now)
            return 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def client_ip() -> str:
    """
    IP do cliente para rate limit.

    Usa só o header de RATELIMIT_IP_HEADER (padrão CF-Connecting-IP): a
    Cloudflare sempre o sobrescreve, enquanto X-Forwarded-For é forjável e
    True-Client-IP só é sobrescrito no plano Enterprise. Sem o header, cai em
    request.remote_addr.
    """
    return _client_ip_and_source()[0]


def client_ip_source() -> str:
    """Fonte do IP nesta requisição (nome do header ou "remote_addr"), sem revelar o IP."""
    return _client_ip_and_source()[1]


def _client_ip_and_source() -> tuple[str, str]:
    name = os.environ.get("RATELIMIT_IP_HEADER", "").strip() or "CF-Connecting-IP"
    value = (request.headers.get(name) or "").strip()
    if value:
        return value[:64], name
    return request.remote_addr or "unknown", "remote_addr"


def _int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def enabled() -> bool:
    """Lê RATELIMIT_ENABLED de app.config ou do ambiente."""
    cfg = current_app.config.get("RATELIMIT_ENABLED")
    if cfg is not None:
        return bool(cfg)
    return os.environ.get("RATELIMIT_ENABLED", "1").lower() not in ("0", "false", "no")


def limits() -> dict:
    """Limites lidos do ambiente a cada chamada."""
    return {
        "login_ip_max": _int_env("RATELIMIT_LOGIN_IP_MAX", 50),  # falhas por IP
        "login_pair_max": _int_env("RATELIMIT_LOGIN_PAIR_MAX", 5),  # falhas por e-mail+IP
        "login_email_max": _int_env("RATELIMIT_LOGIN_EMAIL_MAX", 30),  # falhas por conta, qualquer IP
        "login_window": _int_env("RATELIMIT_LOGIN_WINDOW_SECONDS", 900),
        "signup_ip_max": _int_env("RATELIMIT_SIGNUP_IP_MAX", 10),
        "signup_window": _int_env("RATELIMIT_SIGNUP_WINDOW_SECONDS", 3600),
    }


def too_many(retry_after: int):
    """Resposta 429 padrão com Retry-After."""
    minutes = max(1, -(-retry_after // 60))
    resp = jsonify({"error": f"Muitas tentativas. Tente novamente em {minutes} minutos."})
    resp.status_code = 429
    resp.headers["Retry-After"] = str(retry_after)
    return resp
