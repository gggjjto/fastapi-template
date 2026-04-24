from __future__ import annotations

from app.core.exceptions import DomainError


class InvalidCredentials(DomainError):
    pass


class InvalidToken(DomainError):
    pass
