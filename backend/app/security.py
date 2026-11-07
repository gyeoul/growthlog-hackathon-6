"""Signed, tamper-proof session cookies (HMAC-SHA256, stdlib only)."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

SESSION_COOKIE = "session"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _sign(payload: bytes, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), payload, hashlib.sha256).digest())


def create_session(user_id: int, secret: str, ttl: int) -> str:
    payload = json.dumps({"uid": user_id, "exp": int(time.time()) + ttl}).encode()
    return f"{_b64(payload)}.{_sign(payload, secret)}"


def read_session(token: str, secret: str) -> int | None:
    """Return the user id for a valid, unexpired token; None otherwise."""
    payload_b64, _, signature = token.partition(".")
    if not payload_b64 or not signature:
        return None
    try:
        payload = _unb64(payload_b64)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        return None
    try:
        data: dict[str, Any] = json.loads(payload)
        uid, exp = data["uid"], data["exp"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(uid, int) or not isinstance(exp, int) or exp < time.time():
        return None
    return uid


def new_state() -> str:
    return secrets.token_urlsafe(24)
