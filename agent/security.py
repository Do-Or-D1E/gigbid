"""Shared security helpers: signed service tokens (user identity to MCP servers), and
encryption of OAuth/marketplace tokens at rest (Fernet). Keys only come from env."""
from __future__ import annotations

import os
import time
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken

from agent import settings  # noqa: F401  (loads .env)

AUDIENCE = "gigbid-mcp"


def _secret() -> str:
    secret = os.environ.get("APP_SECRET")
    if not secret:
        raise RuntimeError("APP_SECRET is not set")
    return secret


def mint_service_token(user_id: str, tenant: str, persona: str | None, *, scopes: list[str] | None = None,
                       ttl_s: int = 3600) -> str:
    now = int(time.time())
    claims = {"sub": user_id, "tenant": tenant, "persona": persona, "scopes": scopes or ["read", "write"],
              "aud": AUDIENCE, "iat": now, "exp": now + ttl_s}
    return jwt.encode(claims, _secret(), algorithm="HS256")


def verify_service_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _secret(), algorithms=["HS256"], audience=AUDIENCE)


def _fernet() -> Fernet:
    key = os.environ.get("TOKEN_ENC_KEY")
    if not key:
        raise RuntimeError("TOKEN_ENC_KEY is not set")
    return Fernet(key.encode())


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(cipher: str) -> str:
    try:
        return _fernet().decrypt(cipher.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("token could not be decrypted") from exc
