from __future__ import annotations

from httpx import AsyncClient

_USER_PAYLOAD = {
    "email": "ratelimit@example.com",
    "full_name": "Rate Limit User",
    "password": "Password123!",
}
_LOGIN_PAYLOAD = {"email": "ratelimit@example.com", "password": "Password123!"}


async def test_login_rate_limit(client: AsyncClient) -> None:
    await client.post("/api/v1/users", json=_USER_PAYLOAD)

    for _ in range(10):
        resp = await client.post("/api/v1/auth/token", json=_LOGIN_PAYLOAD)
        assert resp.status_code == 200

    resp = await client.post("/api/v1/auth/token", json=_LOGIN_PAYLOAD)
    assert resp.status_code == 429
    assert resp.json()["code"] == 429


async def test_refresh_rate_limit(client: AsyncClient) -> None:
    await client.post("/api/v1/users", json=_USER_PAYLOAD)
    login_resp = await client.post("/api/v1/auth/token", json=_LOGIN_PAYLOAD)
    refresh_token = login_resp.json()["data"]["refresh_token"]

    for _ in range(20):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 429
    assert resp.json()["code"] == 429
