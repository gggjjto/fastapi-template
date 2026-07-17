from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import InvalidCredentials, InvalidToken
from app.auth.models import AuthSession
from app.auth.repository import AuthSessionRepository
from app.auth.schemas import TokenResponse
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.core.config import get_settings
from app.users.repository import UserRepository

settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.sessions = AuthSessionRepository(session)

    async def login(
        self,
        email: str,
        password: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentials("Invalid email or password")

        session_id = uuid4()
        refresh_token = create_refresh_token(user.id, session_id, uuid4().hex)
        await self.sessions.create_session(
            session_id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.session.commit()
        return TokenResponse(access_token=create_access_token(user.id), refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_refresh_token(refresh_token)
            session_id = UUID(payload["session_id"])
            user_id = UUID(payload["sub"])
        except Exception as exc:
            raise InvalidToken("Invalid or expired refresh token") from exc

        auth_session = await self.sessions.get_by_id(session_id)
        if auth_session is None:
            raise InvalidToken("Invalid or expired refresh token")

        # 会话已撤销，或哈希不匹配（旧的、已轮换的 token 被再次使用）→ 视为复用：
        # 撤销该用户全部会话，强制重新登录。
        token_hash = hash_refresh_token(refresh_token)
        if auth_session.revoked_at is not None or token_hash != auth_session.refresh_token_hash:
            await self.sessions.revoke_all_for_user(user_id)
            await self.session.commit()
            raise InvalidToken("Invalid or expired refresh token")

        # 轮换：颁发新 refresh token，更新会话中的哈希，旧 token 随即失效。
        new_refresh_token = create_refresh_token(user_id, session_id, uuid4().hex)
        await self.sessions.rotate(auth_session, hash_refresh_token(new_refresh_token))
        await self.session.commit()
        return TokenResponse(
            access_token=create_access_token(user_id), refresh_token=new_refresh_token
        )

    async def logout(self, refresh_token: str) -> None:
        """撤销 refresh token 对应的会话。即使会话不存在或已撤销也视为成功，不泄露信息。"""
        auth_session = await self._session_from_token(refresh_token)
        if auth_session is not None:
            await self.sessions.revoke(auth_session)
            await self.session.commit()

    async def logout_all(self, user_id: UUID) -> None:
        await self.sessions.revoke_all_for_user(user_id)
        await self.session.commit()

    async def _session_from_token(self, refresh_token: str) -> AuthSession | None:
        try:
            payload = decode_refresh_token(refresh_token)
            session_id = UUID(payload["session_id"])
        except Exception:
            return None
        return await self.sessions.get_by_id(session_id)
