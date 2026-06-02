from __future__ import annotations


class ErrorCode:
    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    INVALID_TOKEN = "AUTH_INVALID_TOKEN"  # nosec B105 — error code string, not a credential
    INACTIVE_USER = "AUTH_INACTIVE_USER"
