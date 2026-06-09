from __future__ import annotations

from app.core.error_codes import CommonErrorCode


class DomainError(Exception):
    """业务层基础异常，所有领域异常均继承此类。

    携带稳定的业务错误码与 HTTP 状态码，由全局异常处理器统一转换为响应信封。
    `message_key` / `params` 供后续 i18n 阶段做消息翻译，本阶段仅作为占位字段。
    """

    status_code: int = 500
    code: str = CommonErrorCode.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        message_key: str | None = None,
        params: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.message_key = message_key
        self.params = params or {}


class BadRequestError(DomainError):
    status_code = 400
    code = CommonErrorCode.BAD_REQUEST


class UnauthorizedError(DomainError):
    status_code = 401
    code = CommonErrorCode.UNAUTHORIZED


class ForbiddenError(DomainError):
    status_code = 403
    code = CommonErrorCode.FORBIDDEN


class NotFoundError(DomainError):
    status_code = 404
    code = CommonErrorCode.NOT_FOUND


class ConflictError(DomainError):
    status_code = 409
    code = CommonErrorCode.CONFLICT


class ValidationDomainError(DomainError):
    status_code = 422
    code = CommonErrorCode.VALIDATION_ERROR
