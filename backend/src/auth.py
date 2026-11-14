import logging
import os
import re
from datetime import datetime, timezone, timedelta
from functools import wraps

import jwt
from flask import g, jsonify, request

_ALGORITHM = "HS256"


def _carregar_segredo() -> str:
    """Lê JWT_SECRET do ambiente; sem ele o app não sobe."""
    segredo = os.environ.get("JWT_SECRET", "")
    if not segredo.strip():
        raise RuntimeError("JWT_SECRET não definido")
    if len(segredo) < 32:
        # só avisa: não dá para saber o tamanho do segredo já em uso
        logging.getLogger(__name__).warning(
            "JWT_SECRET com menos de 32 caracteres; recomenda-se um valor mais longo."
        )
    return segredo


_SECRET = _carregar_segredo()
_TTL_DAYS = 30

_audit_logger = logging.getLogger("studex.audit")


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=_TTL_DAYS),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def _user_exists(user_id: int) -> bool:
    """Rejeita token válido de usuário que já foi apagado."""
    from database.database import user_exists_db
    return user_exists_db(user_id)


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401
        try:
            payload = jwt.decode(auth[7:], _SECRET, algorithms=[_ALGORITHM])
            g.user_id = int(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
            # Payload sem "sub" ou com "sub" não numérico também é 401, não 500.
            return jsonify({"error": "invalid token"}), 401
        if "user_id" in kwargs and kwargs["user_id"] != g.user_id:
            return jsonify({"error": "forbidden"}), 403
        if not _user_exists(g.user_id):
            return jsonify({"error": "invalid token"}), 401
        return fn(*args, **kwargs)
    return wrapper


def _admin_ids() -> set[int]:
    """IDs de ADMIN_USER_IDS (lista separada por vírgula), lidos a cada chamada."""
    raw = os.environ.get("ADMIN_USER_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if re.fullmatch(r"[0-9]+", part):  # isdigit() aceitaria dígitos unicode
            ids.add(int(part))
    return ids


def is_admin(user_id: int) -> bool:
    return user_id in _admin_ids()


def require_admin(fn):
    """Exige token válido de um usuário em ADMIN_USER_IDS; o acesso é logado só com o id."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401
        try:
            payload = jwt.decode(auth[7:], _SECRET, algorithms=[_ALGORITHM])
            g.user_id = int(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
            # Payload sem "sub" ou com "sub" não numérico também é 401, não 500.
            return jsonify({"error": "invalid token"}), 401
        if not is_admin(g.user_id):
            return jsonify({"error": "forbidden"}), 403
        # Token ainda válido de usuário já removido não pode ser admin.
        if not _user_exists(g.user_id):
            return jsonify({"error": "invalid token"}), 401
        _audit_logger.info("admin_access user_id=%s path=%s method=%s",
                           g.user_id, request.path, request.method)
        return fn(*args, **kwargs)
    return wrapper
