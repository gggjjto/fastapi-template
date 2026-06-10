from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.health import router as health_router


async def test_health_endpoints(client: AsyncClient) -> None:
    live_response = await client.get("/api/v1/health/live")
    ready_response = await client.get("/api/v1/health/ready")

    assert live_response.status_code == 200
    assert live_response.json()["code"] == "OK"
    assert live_response.json()["data"]["status"] == "alive"

    assert ready_response.status_code == 200
    assert ready_response.json()["code"] == "OK"
    assert ready_response.json()["data"]["status"] == "ready"


async def test_ready_without_redis(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    monkeypatch.setattr(health_router.settings, "redis_url", None)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ready"
    assert body["data"]["database"] == "ok"
    assert "redis" not in body["data"]
