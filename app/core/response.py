from __future__ import annotations

from typing import Any

from pydantic import Field

from app.core.schemas import CustomModel


class ApiResponse[T](CustomModel):
    code: int = Field(default=200, ge=100, le=599, description="业务状态码，与 HTTP 状态码一致")
    message: str = Field(default="success", description="响应描述")
    data: T | None = Field(default=None, description="响应数据，错误时为 null")

    @classmethod
    def ok(cls, data: T) -> ApiResponse[T]:
        return cls(data=data)

    @classmethod
    def error(cls, code: int, message: str, data: Any = None) -> ApiResponse[Any]:
        return cls(code=code, message=message, data=data)
