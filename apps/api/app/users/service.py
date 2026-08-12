from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import constants as auth_constants
from app.auth.repository import RbacRepository
from app.auth.security import hash_password
from app.users.exceptions import UserEmailConflict
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate

_USER_EMAIL_CONSTRAINT = "uq_users_email"


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.rbac = RbacRepository(session)

    async def create_user(self, payload: UserCreate) -> User:
        try:
            # ponytail: serializes signup for first-admin determinism;
            # use a bootstrap flow if signup throughput matters.
            await self._lock_user_creation()
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

            role_name = (
                auth_constants.RoleName.ADMIN if is_first_user else auth_constants.RoleName.USER
            )
            role = await self.rbac.get_role_by_name(role_name)
            if role is None:
                raise RuntimeError(f"Default role not found: {role_name}")
            await self.rbac.assign_role_to_user(user.id, role.id)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError as exc:
            await self.session.rollback()
            if self._is_user_email_conflict(exc):
                raise UserEmailConflict("Email already exists") from exc
            raise
        except UserEmailConflict:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def list_users(self, limit: int, offset: int) -> tuple[list[User], int]:
        return await self.users.list_users(limit=limit, offset=offset)

    async def _lock_user_creation(self) -> None:
        dialect = self.session.get_bind().dialect.name
        if dialect == "sqlite":
            await self.session.execute(text("BEGIN IMMEDIATE"))
            return
        if dialect == "postgresql":
            await self.session.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))

    @staticmethod
    def _is_user_email_conflict(exc: IntegrityError) -> bool:
        orig = exc.orig
        constraint_name = getattr(orig, "constraint_name", None)
        if constraint_name == _USER_EMAIL_CONSTRAINT:
            return True
        error = str(orig)
        return _USER_EMAIL_CONSTRAINT in error or "users.email" in error
