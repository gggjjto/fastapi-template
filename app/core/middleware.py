from __future__ import annotations

import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import bind_request_id, clear_request_context

REQUEST_ID_HEADER = "x-request-id"

logger = structlog.get_logger(__name__)


class RequestIDMiddleware:
    """请求 ID 与访问日志中间件（纯 ASGI 实现，不使用 BaseHTTPMiddleware）。

    - 从请求头读取 X-Request-ID；缺失则生成 UUID v4，并绑定到 structlog 上下文
    - 在响应头回写 X-Request-ID，方便客户端与网关追踪
    - 每个 HTTP 请求结束后输出一条 `http.request` 访问日志
      （method / path / status_code / duration_ms / client_ip，并自动携带
      上下文中的 request_id / user_id）
    - 请求结束清理上下文，防止协程复用时泄漏
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = _extract_request_id(scope) or str(uuid.uuid4())
        bind_request_id(request_id)
        status_code: int | None = None
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            if scope["type"] == "http":
                client = scope.get("client")
                logger.info(
                    "http.request",
                    method=scope.get("method"),
                    path=scope.get("path"),
                    status_code=status_code,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                    client_ip=client[0] if client else None,
                )
        finally:
            clear_request_context()


def _extract_request_id(scope: Scope) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == REQUEST_ID_HEADER.encode():
            return value.decode()
    return None
