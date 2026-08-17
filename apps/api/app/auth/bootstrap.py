from __future__ import annotations

import argparse
import asyncio
import getpass
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import RoleName
from app.auth.models import Role, UserRole
from app.auth.repository import RbacRepository
from app.auth.security import hash_password, validate_bcrypt_password_length
from app.auth.seed import ensure_default_rbac
from app.db.session import AsyncSessionLocal, close_db
from app.users.repository import UserRepository


async def bootstrap_platform_admin(
    session: AsyncSession, *, email: str, full_name: str, password: str
) -> None:
    validate_bcrypt_password_length(password)
    await ensure_default_rbac(session)
    platform_role = await session.scalar(
        select(Role).where(Role.name == RoleName.PLATFORM_ADMIN).with_for_update()
    )
    if platform_role is None:
        raise RuntimeError("Platform administrator role is missing")
    existing_admin = await session.scalar(
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.name == RoleName.PLATFORM_ADMIN)
        .limit(1)
    )
    if existing_admin is not None:
        raise RuntimeError("A platform administrator already exists")
    users = UserRepository(session)
    if await users.get_by_email(email) is not None:
        raise RuntimeError("A user with this email already exists")
    user = await users.create(
        email=email.lower(), full_name=full_name, hashed_password=hash_password(password)
    )
    await RbacRepository(session).assign_role_to_user(user.id, platform_role.id)
    await session.commit()


async def _run(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as session:
        await bootstrap_platform_admin(
            session, email=args.email, full_name=args.full_name, password=args.password
        )
    await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first platform administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()
    args.password = os.getenv("APP_BOOTSTRAP_PASSWORD") or getpass.getpass("Password: ")
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
