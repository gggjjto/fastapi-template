from __future__ import annotations


class ErrorCode:
    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    INVALID_TOKEN = "AUTH_INVALID_TOKEN"  # nosec B105 — error code string, not a credential
    INACTIVE_USER = "AUTH_INACTIVE_USER"
    PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"


class Permission:
    """auth 域权限码，格式 resource:action。"""

    ROLES_READ = "roles:read"
    ROLES_MANAGE = "roles:manage"


class RoleName:
    ADMIN = "admin"
    USER = "user"
