"""
Rate limiting em memória (janela deslizante), sem dependências externas.

ATENÇÃO (escala): o estado vive no processo. Em produção o gunicorn roda com
1 worker + 8 threads, então um único dicionário protegido por lock é correto.
Com mais de 1 worker ou mais de 1 instância, cada processo teria seu próprio
contador (o limite efetivo multiplicaria) e este módulo deve migrar para um
armazenamento compartilhado (ex.: Redis).

LGPD: só guardamos timestamps associados a chaves opacas (HMAC-SHA256 com
chave aleatória do processo, para IP e e-mail). Nenhum identificador é
logado. Timestamps vencidos são descartados a cada acesso.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque

from flask import current_app, jsonify, request

_MAX_KEYS = 50_000  # trava de segurança contra crescimento ilimitado da memória

# Chave aleatória só deste processo (nunca persistida): as chaves de IP e
# e-mail são HMAC-SHA256 com ela, então nem um dump de memória revela IP/e-mail
# e o hash não pode ser revertido por enumeração.
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
        # chave -> [janela_em_segundos, deque de timestamps]; cada chave
        # expira pela PRÓPRIA janela.
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
            # Sem clear(): remove as chaves com último hit mais antigo até
            # ficar abaixo de 90% do teto (não zera quem está bloqueado).
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
    IP do cliente para fins de rate limit.

    O Render fica atrás da Cloudflare e seu proxy só ANEXA ao X-Forwarded-For
    (não limpa), então XFF é forjável e remote_addr é o IP do proxy (todos os
    usuários pareceriam um só). Por isso usamos SOMENTE o header de
    RATELIMIT_IP_HEADER (default "CF-Connecting-IP"), que a Cloudflare define
    e sobrescreve em todos os planos. NÃO usamos True-Client-IP: ele só é
    sobrescrito no plano Enterprise; nos demais o cliente poderia enviar o
    próprio True-Client-IP e girá-lo para burlar todos os limites por IP.
    Sem o header, cai em request.remote_addr. Se o /admin/status mostrar
    "remote_addr" em produção, o limite por IP vira GLOBAL (todos compartilham
    o IP do proxy) e RATELIMIT_IP_HEADER precisa ser corrigido. Em dev local,
    sem Cloudflare, o header seria forjável; irrelevante, pois o IP só serve
    para limitar.
    """
    return _client_ip_and_source()[0]


def client_ip_source() -> str:
    """Qual fonte forneceu o IP nesta requisição (nome do header ou
    "remote_addr"). Não revela o IP; serve para o admin conferir no
    /admin/status se o Render está mesmo enviando o header da Cloudflare.
    Se aparecer "remote_addr" em produção, o limite por IP vira global."""
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
    """Desligável via app.config["RATELIMIT_ENABLED"] (testes) ou env."""
    cfg = current_app.config.get("RATELIMIT_ENABLED")
    if cfg is not None:
        return bool(cfg)
    return os.environ.get("RATELIMIT_ENABLED", "1").lower() not in ("0", "false", "no")


def limits() -> dict:
    """Limites configuráveis por env (lidos a cada requisição)."""
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
    minutes = max(1, -(-retry_after // 60))  # ceil
    resp = jsonify({"error": f"Muitas tentativas. Tente novamente em {minutes} minutos."})
    resp.status_code = 429
    resp.headers["Retry-After"] = str(retry_after)
    return resp
