from __future__ import annotations

import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "x-request-id"


class RequestIDMiddleware:
    """
    请求 ID 中间件（纯 ASGI 实现，不使用 BaseHTTPMiddleware）。

    - 从请求头读取 X-Request-ID；若缺失则自动生成 UUID v4
    - 将 request_id 绑定到 structlog 上下文，同一请求内所有日志行自动携带
    - 在响应头中回写 X-Request-ID，方便客户端和网关追踪
    - 请求结束后清理上下文，防止协程复用时 ID 泄漏
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = _extract_request_id(scope) or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.clear_contextvars()


def _extract_request_id(scope: Scope) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == REQUEST_ID_HEADER.encode():
            return value.decode()
    return None
