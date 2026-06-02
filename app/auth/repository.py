from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AuthSession


class AuthSessionRepository:
    """auth_sessions 表的所有数据库读写。不在此层提交事务，由 service 层统一 commit。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthSession:
        auth_session = AuthSession(
            id=session_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(auth_session)
        await self.session.flush()
        return auth_session

    async def get_by_id(self, session_id: uuid.UUID) -> AuthSession | None:
        result = await self.session.execute(select(AuthSession).where(AuthSession.id == session_id))
        return result.scalar_one_or_none()

    async def rotate(self, auth_session: AuthSession, new_refresh_token_hash: str) -> None:
        auth_session.refresh_token_hash = new_refresh_token_hash
        await self.session.flush()

    async def revoke(self, auth_session: AuthSession) -> None:
        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(UTC)
            await self.session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self.session.flush()
