from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import constants as auth_constants
from app.auth.repository import RbacRepository
from app.auth.security import hash_password
from app.users.exceptions import UserEmailConflict
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate

_USER_EMAIL_CONSTRAINTS = {"ix_users_email", "uq_users_email"}


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.rbac = RbacRepository(session)

    async def create_user(self, payload: UserCreate) -> User:
        try:
            existing = await self.users.get_by_email(str(payload.email))
            if existing is not None:
                raise UserEmailConflict("Email already exists")

            user = await self.users.create(
                email=str(payload.email),
                full_name=payload.full_name,
                hashed_password=hash_password(payload.password),
            )

            role_name = auth_constants.RoleName.USER
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

    @staticmethod
    def _is_user_email_conflict(exc: IntegrityError) -> bool:
        orig = exc.orig
        constraint_name = getattr(orig, "constraint_name", None)
        if constraint_name in _USER_EMAIL_CONSTRAINTS:
            return True
        error = str(orig)
        return any(name in error for name in _USER_EMAIL_CONSTRAINTS) or "users.email" in error
