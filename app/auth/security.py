from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: UUID) -> str:
    return _encode(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID, session_id: UUID, jti: str) -> str:
    """颁发 refresh token：绑定服务端会话 id 与一次性 jti，用于轮换与复用检测。"""
    return _encode(
        {"sub": str(user_id), "type": "refresh", "session_id": str(session_id), "jti": jti},
        timedelta(days=settings.refresh_token_expire_days),
    )


def hash_refresh_token(token: str) -> str:
    """对 refresh token 取 sha256，仅存哈希，绝不持久化原始 token。"""
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Not a refresh token")
    return payload


def _encode(claims: dict[str, Any], expire_delta: timedelta) -> str:
    payload = {**claims, "exp": datetime.now(UTC) + expire_delta}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
