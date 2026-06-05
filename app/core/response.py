from __future__ import annotations

from typing import Any

from pydantic import Field

from app.core.error_codes import CommonErrorCode
from app.core.schemas import CustomModel


class ApiResponse[T](CustomModel):
    code: str = Field(
        default=CommonErrorCode.OK, description="业务错误码，成功为 OK，错误为稳定的字符串标识"
    )
    message: str = Field(default="success", description="响应描述，可被本地化")
    data: T | None = Field(default=None, description="响应数据，错误时为 null")
    request_id: str | None = Field(default=None, description="请求 ID，便于客户端与日志关联追踪")

    @classmethod
    def ok(cls, data: T, message: str = "success") -> ApiResponse[T]:
        return cls(data=data, message=message)

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        data: Any = None,
        request_id: str | None = None,
    ) -> ApiResponse[Any]:
        return cls(code=code, message=message, data=data, request_id=request_id)
