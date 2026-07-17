from __future__ import annotations

import structlog

# 请求级上下文统一存放在 structlog 的 contextvars 中，
# 由 logging 的 merge_contextvars 处理器自动并入每条日志，避免重复传参。


def bind_request_id(request_id: str) -> None:
    structlog.contextvars.bind_contextvars(request_id=request_id)


def bind_user_id(user_id: str) -> None:
    structlog.contextvars.bind_contextvars(user_id=user_id)


def bind_tenant_id(tenant_id: str) -> None:
    # 预留：当前未启用多租户，引入租户模型后在鉴权处绑定
    structlog.contextvars.bind_contextvars(tenant_id=tenant_id)


def get_request_context() -> dict[str, object]:
    return dict(structlog.contextvars.get_contextvars())


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()
