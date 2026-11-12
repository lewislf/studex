"""
Testes de segurança de usuários: GET /users admin-only, validação de
cadastro, e-mail case-insensitive e rate limiting.

As rotas usam o DB_PATH padrão, então redirecionamos as funções *_db da
rota para o banco temporário (functools.partial com db_path).
"""

import sqlite3
from functools import partial

import pytest

import rate_limit
from database.database import (
    save_user_db,
    login_user_db,
    get_user_by_email_db,
    _open_connection,
)
from main import app
import routes.user_routes as ur


@pytest.fixture
def real_db(client, temp_db, monkeypatch):
    """Roteia as chamadas de DB das rotas de usuário para o banco temporário."""
    monkeypatch.setattr(ur, "save_user_db", partial(save_user_db, db_path=temp_db))
    monkeypatch.setattr(ur, "login_user_db", partial(login_user_db, db_path=temp_db))
    # contadores/streak leem o DB padrão; não são o foco destes testes
    monkeypatch.setattr(ur, "_live_counters", lambda uid: {})
    monkeypatch.setattr(ur, "_gamification_with_streak", lambda usr, g: {})
    return temp_db


@pytest.fixture
def limited(client):
    """Liga o rate limit (desligado por padrão nos testes) e zera o estado."""
    app.config["RATELIMIT_ENABLED"] = True
    rate_limit.limiter.clear()
    yield
    rate_limit.limiter.clear()
    app.config["RATELIMIT_ENABLED"] = False


GOOD = {"name": "Maria", "email": "maria@email.com", "password": "senha1234"}


# ---------------------------------------------------------------- GET /users

def test_list_users_without_token_401(client):
    assert client.get("/users").status_code == 401


def test_list_users_non_admin_403(client, auth_headers, monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "99")
    assert client.get("/users", headers=auth_headers(1)).status_code == 403


def test_list_users_no_admins_configured_403(client, auth_headers, monkeypatch):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    assert client.get("/users", headers=auth_headers(1)).status_code == 403


def test_list_users_admin_200_without_hash(client, auth_headers, monkeypatch):
    from types import SimpleNamespace
    import database.database as dbmod
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setattr(dbmod, "get_user_db", lambda uid: object())
    u = SimpleNamespace(id=1, name="A", email="a@a.com", hash_password="$argon2id$segredo",
                        gamification={"x": 1}, counters={})
    monkeypatch.setattr(ur, "get_users_db", lambda name: [u])
    monkeypatch.setattr(ur, "_live_counters", lambda uid: {"summaries": 0})
    monkeypatch.setattr(ur, "_gamification_with_streak", lambda usr, g: {"streak": 0})

    resp = client.get("/users", headers=auth_headers(1))
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body[0]) == {"id", "name", "email", "counters", "gamification"}
    assert "argon2" not in resp.get_data(as_text=True)


# ------------------------------------------------------- validação do signup

@pytest.mark.parametrize("payload", [
    {"email": "a@b.com", "password": "senha1234"},                       # sem nome
    {"name": "   ", "email": "a@b.com", "password": "senha1234"},        # nome vazio
    {"name": "x" * 101, "email": "a@b.com", "password": "senha1234"},    # nome longo
    {"name": 5, "email": "a@b.com", "password": "senha1234"},            # tipo errado
    {"name": "M", "password": "senha1234"},                              # sem email
    {"name": "M", "email": "sem-arroba", "password": "senha1234"},
    {"name": "M", "email": "a@b", "password": "senha1234"},              # sem ponto no domínio
    {"name": "M", "email": "a b@c.com", "password": "senha1234"},        # espaço
    {"name": "M", "email": "a@@c.com", "password": "senha1234"},
    {"name": "M", "email": "a" * 250 + "@b.com", "password": "senha1234"},  # > 254
    {"name": "M", "email": ["a@b.com"], "password": "senha1234"},
    {"name": "M", "email": "a@b.com"},                                   # sem senha
    {"name": "M", "email": "a@b.com", "password": "curta"},              # < 8
    {"name": "M", "email": "a@b.com", "password": "x" * 129},            # > 128
    {"name": "M", "email": "a@b.com", "password": 12345678},             # tipo errado
])
def test_signup_invalid_payload_400(client, real_db, payload):
    resp = client.post("/users", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_signup_not_json_400(client, real_db):
    resp = client.post("/users", data="não é json", content_type="text/plain")
    assert resp.status_code == 400
    resp = client.post("/users", json=["lista"])
    assert resp.status_code == 400


def test_signup_boundaries_ok_and_normalised(client, real_db):
    payload = {"name": "  " + "n" * 100 + "  ", "email": "  Maria@Email.COM ", "password": "x" * 128}
    resp = client.post("/users", json=payload)
    assert resp.status_code == 201
    user = get_user_by_email_db("maria@email.com", db_path=real_db)
    assert user.email == "maria@email.com"
    assert user.name == "n" * 100


def test_signup_ignores_client_gamification_and_counters(client, real_db):
    resp = client.post("/users", json={**GOOD, "gamification": {"current_streak": 999},
                                       "counters": {"summaries": 999}})
    assert resp.status_code == 201
    user = get_user_by_email_db(GOOD["email"], db_path=real_db)
    assert user.gamification == {"current_streak": 0, "active_yesterday": False}
    assert user.counters["summaries"] == 0


# --------------------------------------------- e-mail case-insensitive / legado

def test_signup_duplicate_case_insensitive_409(client, real_db):
    assert client.post("/users", json=GOOD).status_code == 201
    resp = client.post("/users", json={**GOOD, "email": "MARIA@Email.com"})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "Email já cadastrado"


def test_signup_rejects_when_legacy_mixed_case_exists(client, real_db):
    save_user_db("Leg", "abc", "Legado@Email.com", db_path=real_db)
    resp = client.post("/users", json={**GOOD, "email": "legado@email.com"})
    assert resp.status_code == 409


def test_legacy_mixed_case_account_still_logs_in(client, real_db):
    # conta antiga: e-mail com maiúsculas e senha curta (< 8)
    save_user_db("Leg", "abc", "Legado@Email.com", db_path=real_db)
    for email in ("Legado@Email.com", "legado@email.com", "LEGADO@EMAIL.COM"):
        resp = client.post("/users/login", json={"email": email, "password": "abc"})
        assert resp.status_code == 200, email
    # e-mail armazenado não foi reescrito
    with _open_connection(real_db) as conn:
        assert conn.execute("SELECT email FROM users").fetchone()[0] == "Legado@Email.com"


def test_login_wrong_password_401_and_bad_types_400(client, real_db):
    save_user_db("Leg", "abc", "l@e.com", db_path=real_db)
    assert client.post("/users/login", json={"email": "l@e.com", "password": "errada"}).status_code == 401
    assert client.post("/users/login", json={"email": "l@e.com", "password": 123}).status_code == 400
    assert client.post("/users/login", json={"email": "l@e.com", "password": "x" * 1025}).status_code == 400
    assert client.post("/users/login", json={"email": "l@e.com"}).status_code == 400


# ------------------------------------------------------------- auth.py

@pytest.mark.real_user_check
def test_admin_token_of_deleted_user_401(client, auth_headers, monkeypatch):
    import database.database as dbmod
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    monkeypatch.setattr(dbmod, "user_exists_db", lambda uid: False)
    assert client.get("/users", headers=auth_headers(1)).status_code == 401


@pytest.mark.real_user_check
def test_normal_route_token_of_deleted_user_401(client, real_db, auth_headers, monkeypatch):
    import database.database as dbmod
    scoped = partial(dbmod.get_user_db, db_path=real_db)
    monkeypatch.setattr(dbmod, "user_exists_db", partial(dbmod.user_exists_db, db_path=real_db))
    monkeypatch.setattr(ur, "get_user_db", scoped)
    uid = save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    assert client.get(f"/users/{uid}", headers=auth_headers(uid)).status_code == 200
    dbmod.delete_user_db(uid, db_path=real_db)
    assert client.get(f"/users/{uid}", headers=auth_headers(uid)).status_code == 401


def test_token_without_or_bad_sub_is_401_not_500(client, monkeypatch):
    import jwt as pyjwt
    import auth
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    for payload in ({"foo": 1}, {"sub": "abc"}, {"sub": None}, {"sub": [1]}):
        tok = pyjwt.encode(payload, auth._SECRET, algorithm="HS256")
        h = {"Authorization": f"Bearer {tok}"}
        assert client.get("/users", headers=h).status_code == 401, payload
        assert client.get("/users/1", headers=h).status_code == 401, payload


def test_admin_ids_ignore_unicode_digits(monkeypatch):
    import auth
    monkeypatch.setenv("ADMIN_USER_IDS", "1, ٣ ,x,2²,7")
    assert auth._admin_ids() == {1, 7}


# ------------------------------------------------------------- rate limiting

def test_limiter_sliding_window_expires():
    t = [0.0]
    lim = rate_limit.SlidingWindowLimiter(clock=lambda: t[0])
    for _ in range(3):
        lim.record("k", 10)
    assert lim.retry_after("k", 3, 10) > 0
    t[0] = 11.0
    assert lim.retry_after("k", 3, 10) == 0
    assert lim._hits == {}  # entradas vencidas descartadas


def test_limiter_check_and_record_atomic_limit():
    lim = rate_limit.SlidingWindowLimiter(clock=lambda: 0.0)
    assert [lim.check_and_record("k", 2, 10) for _ in range(2)] == [0, 0]
    assert lim.check_and_record("k", 2, 10) > 0
    assert len(lim._hits["k"][1]) == 2  # a tentativa bloqueada não é registrada


def test_limiter_each_key_expires_by_own_window():
    t = [0.0]
    lim = rate_limit.SlidingWindowLimiter(clock=lambda: t[0])
    lim.record("curta", 10)
    lim.record("longa", 1000)
    t[0] = 500.0
    lim._ops = 499
    lim.record("x", 10)  # dispara varredura
    assert "curta" not in lim._hits and "longa" in lim._hits


def test_limiter_max_keys_evicts_oldest_not_clear(monkeypatch):
    monkeypatch.setattr(rate_limit, "_MAX_KEYS", 100)
    t = [0.0]
    lim = rate_limit.SlidingWindowLimiter(clock=lambda: t[0])
    for i in range(100):
        t[0] = float(i)
        lim.record(f"k{i}", 10_000)
    lim._ops = 499
    t[0] = 200.0
    lim.record("novo", 10_000)
    assert 0 < len(lim._hits) < 100
    assert "novo" in lim._hits and "k99" in lim._hits and "k0" not in lim._hits


def test_client_ip_header_order(client, monkeypatch):
    monkeypatch.delenv("RATELIMIT_IP_HEADER", raising=False)
    def ip(headers):
        with app.test_request_context("/", headers=headers, environ_base={"REMOTE_ADDR": "10.0.0.9"}):
            return rate_limit.client_ip()
    assert ip({}) == "10.0.0.9"
    assert ip({"CF-Connecting-IP": "2.2.2.2"}) == "2.2.2.2"
    # True-Client-IP é forjável fora do plano Enterprise: ignorado
    assert ip({"CF-Connecting-IP": "2.2.2.2", "True-Client-IP": "1.1.1.1"}) == "2.2.2.2"
    assert ip({"True-Client-IP": "1.1.1.1"}) == "10.0.0.9"
    assert ip({"X-Forwarded-For": "6.6.6.6"}) == "10.0.0.9"  # XFF é ignorado
    monkeypatch.setenv("RATELIMIT_IP_HEADER", "X-Meu-IP")
    assert ip({"X-Meu-IP": "3.3.3.3", "CF-Connecting-IP": "1.1.1.1"}) == "3.3.3.3"
    assert ip({"CF-Connecting-IP": "1.1.1.1"}) == "10.0.0.9"  # só o header configurado vale


def test_true_client_ip_rotation_does_not_bypass_limit(client, real_db, limited):
    save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    def attempt(i):
        return client.post("/users/login", json={"email": "m@e.com", "password": "x"},
                           headers={"CF-Connecting-IP": "7.7.7.7", "True-Client-IP": f"5.5.5.{i}"})
    for i in range(5):
        assert attempt(i).status_code == 401
    assert attempt(99).status_code == 429


def _login(client, email, pw, ip="1.1.1.1"):
    return client.post("/users/login", json={"email": email, "password": pw},
                       headers={"CF-Connecting-IP": ip})


def test_login_pair_blocks_after_5_failures_429(client, real_db, limited):
    save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    for _ in range(5):
        assert _login(client, "m@e.com", "x").status_code == 401
    resp = _login(client, "M@E.com", "senha1234")
    assert resp.status_code == 429
    assert resp.headers["Retry-After"].isdigit()
    assert resp.get_json()["error"].startswith("Muitas tentativas. Tente novamente em ")


def test_other_ip_not_blocked_by_attacker_pair(client, real_db, limited):
    save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    for _ in range(5):
        _login(client, "m@e.com", "x", ip="6.6.6.6")
    assert _login(client, "m@e.com", "x", ip="6.6.6.6").status_code == 429
    assert _login(client, "m@e.com", "senha1234", ip="2.2.2.2").status_code == 200


def test_account_cap_blocks_even_correct_password_then_expires(client, real_db, limited, monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(rate_limit.limiter, "_clock", lambda: t[0])
    save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    for i in range(30):  # força bruta distribuída: 30 falhas de IPs diferentes
        assert _login(client, "m@e.com", "x", ip=f"9.9.{i}.1").status_code == 401
    # sem oráculo: senha correta de IP novo também recebe 429
    assert _login(client, "m@e.com", "senha1234", ip="9.9.99.2").status_code == 429
    assert _login(client, "m@e.com", "x", ip="9.9.99.3").status_code == 429
    t[0] += 901  # janela vencida
    assert _login(client, "m@e.com", "senha1234", ip="9.9.99.2").status_code == 200


def test_every_wrong_password_is_recorded(client, real_db, limited, monkeypatch):
    save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    em = rate_limit.normalise_email("m@e.com")
    acc_key = rate_limit.mac_key("lacc", em)
    for i in range(35):
        _login(client, "m@e.com", "x", ip=f"8.8.{i}.1")
    # as 30 primeiras falhas contam; as demais são barradas antes da senha
    # (429), então o contador para no teto, sem passar por caminho sem registro
    assert len(rate_limit.limiter._hits[acc_key][1]) == 30
    # falha com conta sob teto não existe sem registro: IP novo, e-mail outro
    assert _login(client, "outro@e.com", "x", ip="7.7.7.7").status_code == 401
    assert len(rate_limit.limiter._hits[rate_limit.mac_key("lacc", "outro@e.com")][1]) == 1


def test_login_successes_do_not_count_for_ip_limit(client, real_db, limited, monkeypatch):
    monkeypatch.setenv("RATELIMIT_LOGIN_IP_MAX", "3")
    save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    for _ in range(10):  # sucessos não consomem o teto por IP
        assert _login(client, "m@e.com", "senha1234").status_code == 200


def test_login_pair_reset_on_success(client, real_db, limited):
    save_user_db("M", "senha1234", "m@e.com", db_path=real_db)
    for _ in range(4):
        _login(client, "m@e.com", "x")
    assert _login(client, "m@e.com", "senha1234").status_code == 200
    for _ in range(4):
        assert _login(client, "m@e.com", "x").status_code == 401


def test_login_per_ip_failures_limit_429(client, real_db, limited, monkeypatch):
    monkeypatch.setenv("RATELIMIT_LOGIN_IP_MAX", "3")
    for i in range(3):
        assert _login(client, f"u{i}@e.com", "x").status_code == 401
    resp = _login(client, "outro@e.com", "x")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_login_limit_expires_after_window(client, real_db, limited, monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(rate_limit.limiter, "_clock", lambda: t[0])
    for _ in range(5):
        _login(client, "m@e.com", "x")
    assert _login(client, "m@e.com", "x").status_code == 429
    t[0] += 901
    assert _login(client, "m@e.com", "x").status_code == 401


def test_signup_per_ip_limit_429(client, real_db, limited, monkeypatch):
    monkeypatch.setenv("RATELIMIT_SIGNUP_IP_MAX", "3")
    for i in range(3):
        assert client.post("/users", json={**GOOD, "email": f"u{i}@e.com"}).status_code == 201
    resp = client.post("/users", json={**GOOD, "email": "novo@e.com"})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_signup_validation_errors_do_not_consume_quota(client, real_db, limited):
    for _ in range(15):
        assert client.post("/users", json={"name": "x"}).status_code == 400
    assert client.post("/users", json=GOOD).status_code == 201


def test_limiter_keys_and_logs_have_no_identifiers(client, real_db, limited, caplog):
    import logging
    with caplog.at_level(logging.DEBUG):
        for _ in range(6):
            _login(client, "segredo@e.com", "x", ip="8.8.4.4")
    assert all("segredo" not in k and "8.8.4.4" not in k for k in rate_limit.limiter._hits)
    txt = caplog.text
    assert "segredo" not in txt and "8.8.4.4" not in txt
    assert "login bloqueado por par" in txt



def test_nonascii_legacy_email_logs_in_and_blocks_duplicate(client, real_db):
    save_user_db("Leg", "abc", "JOSÉ@x.com", db_path=real_db)
    resp = client.post("/users/login", json={"email": "josé@x.com", "password": "abc"})
    assert resp.status_code == 200
    resp = client.post("/users", json={**GOOD, "email": "josé@x.com"})
    assert resp.status_code == 409


def test_login_ignores_surrounding_spaces_in_email(client, real_db):
    save_user_db("Leg", "abcd", "Espaco@X.com", db_path=real_db)
    r = client.post("/users/login", json={"email": "  espaco@x.com ", "password": "abcd"})
    assert r.status_code == 200
