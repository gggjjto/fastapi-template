from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth import constants as auth_constants
from app.auth.repository import RbacRepository
from app.auth.security import decode_access_token
from app.core.exceptions import ForbiddenError
from app.db.session import DBSession
from app.users.models import User
from app.users.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

CurrentToken = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(session: DBSession, token: CurrentToken) -> User:
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    user = await UserRepository(session).get_by_id(UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_active_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_active_user)]


class RequirePermission:
    """权限守卫依赖：要求当前用户拥有指定权限码（resource:action）。

    未认证 / 账号停用由 CurrentUser 处理（401 / 403）；
    已认证但缺少权限时抛 ForbiddenError（403，code=AUTH_PERMISSION_DENIED）。
    """

    def __init__(self, permission: str) -> None:
        self.permission = permission

    async def __call__(self, current_user: CurrentUser, session: DBSession) -> None:
        permissions = await RbacRepository(session).get_user_permissions(current_user.id)
        if self.permission not in permissions:
            raise ForbiddenError(
                "Permission denied", code=auth_constants.ErrorCode.PERMISSION_DENIED
            )
