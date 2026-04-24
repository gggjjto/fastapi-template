from __future__ import annotations

from app.auth.security import hash_password
from app.users.exceptions import UserEmailConflict
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def create_user(self, payload: UserCreate) -> User:
        existing = await self.repository.get_by_email(str(payload.email))
        if existing is not None:
            raise UserEmailConflict("Email already exists")
        return await self.repository.create(
            email=str(payload.email),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )

    async def list_users(self, limit: int, offset: int) -> tuple[list[User], int]:
        return await self.repository.list_users(limit=limit, offset=offset)
