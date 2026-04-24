from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.users.repository import UserRepository

_settings = get_settings()

_EMAIL = "auth@example.com"
_PASSWORD = "Password123!"
_USER_PAYLOAD = {"email": _EMAIL, "full_name": "Auth User", "password": _PASSWORD}


async def _register(client: AsyncClient) -> dict:
    resp = await client.post("/api/v1/users", json=_USER_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["data"]


async def _login(client: AsyncClient) -> dict:
    resp = await client.post("/api/v1/auth/token", json={"email": _EMAIL, "password": _PASSWORD})
    assert resp.status_code == 200
    return resp.json()["data"]


async def test_login_success(client: AsyncClient) -> None:
    await _register(client)
    tokens = await _login(client)

    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/token", json={"email": _EMAIL, "password": "WrongPassword!"}
    )

    assert resp.status_code == 401
    assert resp.json()["code"] == 401


async def test_login_unknown_email(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/token", json={"email": "nobody@example.com", "password": _PASSWORD}
    )

    assert resp.status_code == 401


async def test_get_me(client: AsyncClient) -> None:
    await _register(client)
    tokens = await _login(client)

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert resp.status_code == 200
    assert resp.json()["code"] == 200
    user = resp.json()["data"]
    assert user["email"] == _EMAIL
    assert "hashed_password" not in user


async def test_get_me_without_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")

    assert resp.status_code == 401


async def test_get_me_with_invalid_token(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
    )

    assert resp.status_code == 401


async def test_refresh_token(client: AsyncClient) -> None:
    await _register(client)
    tokens = await _login(client)

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert resp.status_code == 200
    new_tokens = resp.json()["data"]
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


async def test_refresh_with_invalid_token(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})

    assert resp.status_code == 401


async def test_cannot_use_refresh_token_as_access_token(client: AsyncClient) -> None:
    await _register(client)
    tokens = await _login(client)

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )

    assert resp.status_code == 401


# ── Branch coverage: paths not exercised above ────────────────────────────────


async def test_get_me_with_expired_token(client: AsyncClient) -> None:
    """Covers the ExpiredSignatureError branch in get_current_user."""
    await _register(client)

    expired = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        },
        _settings.jwt_secret,
        algorithm=_settings.jwt_algorithm,
    )

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert resp.status_code == 401
    assert "expired" in resp.json()["message"].lower()


async def test_get_me_after_user_deleted(client: AsyncClient) -> None:
    """Covers the 'user not found after token decode' branch in get_current_user."""
    user_data = await _register(client)
    tokens = await _login(client)

    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(uuid.UUID(user_data["id"]))
        await session.delete(user)
        await session.commit()

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert resp.status_code == 401


async def test_get_me_inactive_user(client: AsyncClient) -> None:
    """Covers the is_active=False branch in get_current_active_user."""
    user_data = await _register(client)
    tokens = await _login(client)

    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(uuid.UUID(user_data["id"]))
        user.is_active = False
        await session.commit()

    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert resp.status_code == 403
    assert resp.json()["code"] == 403
