from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from app.auth.models import Permission, Role, RolePermission, UserRole
from app.auth.repository import AuthSessionRepository, RbacRepository
from app.auth.security import hash_password, hash_refresh_token
from app.db.session import AsyncSessionLocal
from app.users.models import User
from app.users.repository import UserRepository


async def _create_user(session) -> User:
    return await UserRepository(session).create(
        email=f"{uuid4()}@example.com",
        full_name="Repo User",
        hashed_password=hash_password("Password123!"),
    )


async def test_auth_session_revoke_is_idempotent() -> None:
    async with AsyncSessionLocal() as session:
        user = await _create_user(session)
        repo = AuthSessionRepository(session)
        auth_session = await repo.create_session(
            session_id=uuid4(),
            user_id=user.id,
            refresh_token_hash=hash_refresh_token("seed-token"),
            expires_at=datetime.now(UTC) + timedelta(days=30),
            user_agent=None,
            ip_address=None,
        )

        await repo.revoke(auth_session)
        first = auth_session.revoked_at

        await repo.revoke(auth_session)

        assert first is not None
        assert auth_session.revoked_at == first


async def test_auth_session_rotate_updates_hash() -> None:
    async with AsyncSessionLocal() as session:
        user = await _create_user(session)
        repo = AuthSessionRepository(session)
        auth_session = await repo.create_session(
            session_id=uuid4(),
            user_id=user.id,
            refresh_token_hash=hash_refresh_token("old"),
            expires_at=datetime.now(UTC) + timedelta(days=30),
            user_agent=None,
            ip_address=None,
        )

        await repo.rotate(auth_session, hash_refresh_token("new"))

        assert auth_session.refresh_token_hash == hash_refresh_token("new")


async def test_assign_role_to_user_is_idempotent() -> None:
    async with AsyncSessionLocal() as session:
        user = await _create_user(session)
        role = Role(name="role-test")
        perm = Permission(code="perm:test")
        session.add_all([role, perm])
        await session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=perm.id))
        await session.flush()

        repo = RbacRepository(session)
        await repo.assign_role_to_user(user.id, role.id)
        await repo.assign_role_to_user(user.id, role.id)

        count = (
            await session.execute(
                select(func.count()).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
            )
        ).scalar_one()

        assert count == 1
