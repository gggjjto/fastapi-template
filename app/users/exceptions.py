from __future__ import annotations

from app.core.exceptions import ConflictError, DomainError


class UserNotFound(DomainError):
    pass


class UserEmailConflict(ConflictError):
    pass
