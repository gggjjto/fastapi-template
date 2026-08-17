from __future__ import annotations

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.tenants.constants import ErrorCode


class TenantNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Tenant not found", code=ErrorCode.NOT_FOUND)


class TenantSlugConflict(ConflictError):
    def __init__(self) -> None:
        super().__init__("Tenant slug already exists", code=ErrorCode.SLUG_CONFLICT)


class TenantMemberNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Tenant member not found", code=ErrorCode.MEMBER_NOT_FOUND)


class TenantMemberConflict(ConflictError):
    def __init__(self, message: str = "User is already a tenant member") -> None:
        super().__init__(message, code=ErrorCode.MEMBER_CONFLICT)


class TenantOwnerRequired(ForbiddenError):
    def __init__(self, message: str = "Tenant owner permission required") -> None:
        super().__init__(message, code=ErrorCode.OWNER_REQUIRED)


class TenantInvitationNotFound(NotFoundError):
    def __init__(self) -> None:
        super().__init__("Invitation not found", code=ErrorCode.INVITATION_NOT_FOUND)


class TenantInvitationConflict(ConflictError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.INVITATION_CONFLICT)


class TenantInvitationInvalid(ForbiddenError):
    def __init__(self, message: str = "Invitation is invalid or expired") -> None:
        super().__init__(message, code=ErrorCode.INVITATION_INVALID)


class TenantInvitationAuthenticationRequired(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__(
            "Sign in with the invited email before accepting",
            code=ErrorCode.INVITATION_AUTH_REQUIRED,
        )
