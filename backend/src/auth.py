import os
from datetime import datetime, timezone, timedelta
from functools import wraps

import jwt
from flask import g, jsonify, request

_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
_ALGORITHM = "HS256"
_TTL_DAYS = 30


def create_token(user_id: int) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=_TTL_DAYS),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "unauthorized"}), 401
        try:
            payload = jwt.decode(auth[7:], _SECRET, algorithms=[_ALGORITHM])
            g.user_id = int(payload["sub"])
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401
        if "user_id" in kwargs and kwargs["user_id"] != g.user_id:
            return jsonify({"error": "forbidden"}), 403
        return fn(*args, **kwargs)
    return wrapper
