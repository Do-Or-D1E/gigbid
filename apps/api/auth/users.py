"""Users, password hashing (PBKDF2), web session tokens, and the encrypted marketplace /
OAuth token store. Tokens are never logged and every query is scoped by user id."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid

import jwt
from fastapi import Depends, HTTPException, Request

from agent import db
from agent.security import decrypt, encrypt

WEB_AUD = "gigbid-web"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return "pbkdf2$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def check_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, dig_b64 = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), 200_000)
    return hmac.compare_digest(digest, base64.b64decode(dig_b64))


def session_token(user_id: str, ttl_s: int = 7 * 24 * 3600) -> str:
    now = int(time.time())
    return jwt.encode({"sub": user_id, "aud": WEB_AUD, "iat": now, "exp": now + ttl_s},
                      os.environ["APP_SECRET"], algorithm="HS256")


async def create_user(email: str, password: str, name: str) -> dict:
    uid = "u_" + uuid.uuid4().hex[:12]
    await db.execute("insert into users(id, email, password_hash, name) values (%s,%s,%s,%s)",
                     uid, email.lower(), hash_password(password), name)
    await db.execute("insert into user_settings(user_id, data) values (%s, '{}'::jsonb) on conflict do nothing", uid)
    return await db.fetchone("select * from users where id=%s", uid)


async def current_user(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else request.query_params.get("token")
    if not token:
        raise HTTPException(401, "not signed in")
    try:
        claims = jwt.decode(token, os.environ["APP_SECRET"], algorithms=["HS256"], audience=WEB_AUD)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "session expired") from exc
    user = await db.fetchone("select id, email, name, persona_id from users where id=%s", claims["sub"])
    if not user:
        raise HTTPException(401, "unknown user")
    return user


CurrentUser = Depends(current_user)


# ----------------------------------------------------------------------------- token store
async def store_marketplace_token(user_id: str, mode: str, account_id: str, secret: str | dict,
                                  meta: dict | None = None) -> None:
    value = json.dumps(secret) if isinstance(secret, dict) else secret
    await db.execute(
        "insert into marketplace_accounts(user_id, mode, account_id, enc_token, meta) values (%s,%s,%s,%s,%s)"
        " on conflict (user_id, mode) do update set account_id=excluded.account_id, enc_token=excluded.enc_token,"
        " meta=excluded.meta, created_at=now()", user_id, mode, account_id, encrypt(value), db.jsonb(meta or {}))


async def load_marketplace_token(user_id: str, mode: str) -> str | None:
    row = await db.fetchone("select enc_token from marketplace_accounts where user_id=%s and mode=%s", user_id, mode)
    return decrypt(row["enc_token"]) if row else None
