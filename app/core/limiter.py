from __future__ import annotations

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.error_codes import CommonErrorCode

# 全局限流器，通过 @limiter.limit("N/period") 装饰器应用到具体接口
# 默认以客户端 IP 作为限流 key；如需按用户维度限流，可将 get_remote_address
# 替换为自定义函数（例如从 token 中提取 user_id）
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """触发限流时统一返回 429，格式与 ApiResponse 保持一致。"""
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    return JSONResponse(
        status_code=429,
        content={
            "code": CommonErrorCode.RATE_LIMITED,
            "message": f"请求过于频繁：{exc.detail}",
            "data": None,
            "request_id": request_id if isinstance(request_id, str) else None,
        },
    )
