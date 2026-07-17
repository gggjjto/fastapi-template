from __future__ import annotations

from app.auth.constants import ErrorCode
from app.core.exceptions import UnauthorizedError


class InvalidCredentials(UnauthorizedError):
    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(
            message,
            code=ErrorCode.INVALID_CREDENTIALS,
            message_key="errors.auth.invalid_credentials",
        )


class InvalidToken(UnauthorizedError):
    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(
            message,
            code=ErrorCode.INVALID_TOKEN,
            message_key="errors.auth.invalid_token",
        )
