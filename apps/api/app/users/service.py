from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import constants as auth_constants
from app.auth.repository import RbacRepository
from app.auth.security import hash_password
from app.users.exceptions import UserEmailConflict
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.rbac = RbacRepository(session)

    async def create_user(self, payload: UserCreate) -> User:
        existing = await self.users.get_by_email(str(payload.email))
        if existing is not None:
            raise UserEmailConflict("Email already exists")

        # 第一个注册的用户成为 admin，其余为普通 user
        is_first_user = await self.users.count() == 0
        user = await self.users.create(
            email=str(payload.email),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )

        role_name = auth_constants.RoleName.ADMIN if is_first_user else auth_constants.RoleName.USER
        role = await self.rbac.get_role_by_name(role_name)
        if role is not None:
            await self.rbac.assign_role_to_user(user.id, role.id)
            await self.session.commit()
        return user

    async def list_users(self, limit: int, offset: int) -> tuple[list[User], int]:
        return await self.users.list_users(limit=limit, offset=offset)
