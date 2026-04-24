from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_users(self, limit: int, offset: int) -> tuple[list[User], int]:
        total = (await self.session.execute(select(func.count()).select_from(User))).scalar_one()
        users = list(
            (await self.session.execute(select(User).offset(offset).limit(limit))).scalars().all()
        )
        return users, total

    async def create(self, *, email: str, full_name: str, hashed_password: str) -> User:
        user = User(email=email, full_name=full_name, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
