from __future__ import annotations

import uuid

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import app


# 注册一个仅用于测试的路由，触发未捕获异常以验证兜底处理器。
@app.get("/api/v1/_test_boom", include_in_schema=False)
async def _boom() -> None:
    raise RuntimeError("boom should not leak to the client")


async def test_domain_error_envelope(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}")

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "USER_NOT_FOUND"
    assert body["data"] is None
    assert body["request_id"]  # 由 RequestIDMiddleware 生成并回填


async def test_validation_error_envelope(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "full_name": "", "password": "short"},
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert isinstance(body["data"], list)
    assert body["request_id"]


async def test_unhandled_exception_returns_generic_500() -> None:
    # ServerErrorMiddleware 在发送 500 响应后会重新抛出异常（供 uvicorn 记录日志），
    # 因此这里用 raise_app_exceptions=False 的独立传输，模拟真实服务器：客户端拿到干净的 500。
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/_test_boom")

    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert body["data"] is None
    # 不得泄露堆栈或原始异常信息
    assert "boom" not in body["message"]
    assert "Traceback" not in resp.text


async def test_request_id_is_propagated(client: AsyncClient) -> None:
    provided = "req-test-123"
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers={"X-Request-ID": provided})

    assert resp.status_code == 404
    assert resp.headers["x-request-id"] == provided
    assert resp.json()["request_id"] == provided
