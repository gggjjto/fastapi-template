from __future__ import annotations

from typing import Any

from app.core.schemas import CustomModel


class ApiResponse[T](CustomModel):
    code: int = 200
    message: str = "success"
    data: T | None = None

    @classmethod
    def ok(cls, data: T) -> ApiResponse[T]:
        return cls(data=data)

    @classmethod
    def error(cls, code: int, message: str, data: Any = None) -> ApiResponse[Any]:
        return cls(code=code, message=message, data=data)
