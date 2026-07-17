from __future__ import annotations

from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError
from app.users.constants import ErrorCode


class UserNotFound(NotFoundError):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(
            "User not found",
            code=ErrorCode.USER_NOT_FOUND,
            message_key="errors.user.not_found",
            params={"user_id": str(user_id)},
        )


class UserEmailConflict(ConflictError):
    def __init__(self, message: str = "Email already exists") -> None:
        super().__init__(
            message,
            code=ErrorCode.USER_EMAIL_CONFLICT,
            message_key="errors.user.email_conflict",
        )
