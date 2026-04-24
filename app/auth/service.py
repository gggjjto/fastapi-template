from __future__ import annotations

from uuid import UUID

from app.auth.exceptions import InvalidCredentials, InvalidToken
from app.auth.schemas import TokenResponse
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from app.users.repository import UserRepository


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentials("Invalid email or password")
        return _build_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_refresh_token(refresh_token)
        except Exception as exc:
            raise InvalidToken("Invalid or expired refresh token") from exc
        user = await self.repository.get_by_id(UUID(payload["sub"]))
        if user is None:
            raise InvalidToken("User not found")
        return _build_tokens(user.id)


def _build_tokens(user_id: UUID) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
