from __future__ import annotations

from httpx import AsyncClient


async def test_health_endpoints(client: AsyncClient) -> None:
    live_response = await client.get("/api/v1/health/live")
    ready_response = await client.get("/api/v1/health/ready")

    assert live_response.status_code == 200
    assert live_response.json()["code"] == 200
    assert live_response.json()["data"]["status"] == "alive"

    assert ready_response.status_code == 200
    assert ready_response.json()["code"] == 200
    assert ready_response.json()["data"]["status"] == "ready"
