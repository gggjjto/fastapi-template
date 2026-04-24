from __future__ import annotations

import uuid

from httpx import AsyncClient


async def test_request_id_injected_in_response(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health/live")

    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    # Should be a valid UUID v4
    request_id = resp.headers["x-request-id"]
    uuid.UUID(request_id, version=4)  # raises ValueError if not valid


async def test_custom_request_id_echoed_back(client: AsyncClient) -> None:
    custom_id = "my-trace-id-12345"
    resp = await client.get("/api/v1/health/live", headers={"X-Request-ID": custom_id})

    assert resp.headers["x-request-id"] == custom_id


async def test_each_request_gets_unique_id(client: AsyncClient) -> None:
    resp1 = await client.get("/api/v1/health/live")
    resp2 = await client.get("/api/v1/health/live")

    assert resp1.headers["x-request-id"] != resp2.headers["x-request-id"]
