from __future__ import annotations


class ErrorCode:
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_EMAIL_CONFLICT = "USER_EMAIL_CONFLICT"


class Permission:
    """users 域权限码，格式 resource:action。"""

    READ = "users:read"
    CREATE = "users:create"
    UPDATE = "users:update"
    DELETE = "users:delete"
