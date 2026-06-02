from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.error_codes import CommonErrorCode
from app.core.exceptions import DomainError

logger = structlog.get_logger(__name__)

_HTTP_CODE_MAP: dict[int, str] = {
    400: CommonErrorCode.BAD_REQUEST,
    401: CommonErrorCode.UNAUTHORIZED,
    403: CommonErrorCode.FORBIDDEN,
    404: CommonErrorCode.NOT_FOUND,
    405: "METHOD_NOT_ALLOWED",
    409: CommonErrorCode.CONFLICT,
    422: CommonErrorCode.VALIDATION_ERROR,
    429: CommonErrorCode.RATE_LIMITED,
    500: CommonErrorCode.INTERNAL_SERVER_ERROR,
}


def _current_request_id() -> str | None:
    """读取 RequestIDMiddleware 绑定到 structlog 上下文的 request_id。"""
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    return request_id if isinstance(request_id, str) else None


def _envelope(code: str, message: str, data: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data, "request_id": _current_request_id()}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        log = logger.warning if exc.status_code < 500 else logger.error
        log(
            "domain.error",
            error_code=exc.code,
            status_code=exc.status_code,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        code = _HTTP_CODE_MAP.get(exc.status_code, "ERROR")
        if isinstance(detail, dict) and "message" in detail:
            message = str(detail["message"])
        elif detail:
            message = str(detail)
        else:
            message = code
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(loc) for loc in err["loc"] if loc != "body"),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_envelope(
                CommonErrorCode.VALIDATION_ERROR, "Request validation failed", details
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled.error",
            error_code=CommonErrorCode.INTERNAL_SERVER_ERROR,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content=_envelope(CommonErrorCode.INTERNAL_SERVER_ERROR, "Internal server error"),
        )
