from __future__ import annotations


class ErrorCode:
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_TOKEN = "INVALID_TOKEN"  # nosec B105 — error code string, not a credential
    INACTIVE_USER = "INACTIVE_USER"
