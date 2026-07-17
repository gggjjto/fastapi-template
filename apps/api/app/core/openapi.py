from __future__ import annotations

from typing import Any

from pydantic import Field

from app.core.schemas import CustomModel


class ErrorResponse(CustomModel):
    """统一错误响应信封，供 OpenAPI 文档复用（与全局异常处理器输出一致）。"""

    code: str = Field(description="稳定业务错误码", examples=["NOT_FOUND"])
    message: str = Field(description="错误描述（可本地化）", examples=["Resource not found"])
    data: None = Field(default=None, description="错误时固定为 null")
    request_id: str | None = Field(default=None, description="请求 ID", examples=["..."])


_DESCRIPTIONS: dict[int, str] = {
    400: "请求无效",
    401: "未认证",
    403: "无权限",
    404: "资源不存在",
    409: "资源冲突",
    422: "参数校验失败",
    429: "请求过于频繁",
    500: "服务器内部错误",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """生成可复用的 OpenAPI 错误响应映射，统一使用 ErrorResponse 模型。"""
    return {
        code: {"model": ErrorResponse, "description": _DESCRIPTIONS.get(code, "Error")}
        for code in status_codes
    }
