from __future__ import annotations

from sqlalchemy import select

from app.auth import constants as auth_constants
from app.auth.models import Permission, Role, RolePermission
from app.auth.seed import ALL_PERMISSIONS, ensure_default_rbac
from app.db.session import AsyncSessionLocal


async def _permission_codes() -> set[str]:
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Permission.code))).scalars().all()
        return set(rows)


async def _role_permission_codes(role_name: str) -> set[str]:
    async with AsyncSessionLocal() as session:
        role_id = (
            await session.execute(select(Role.id).where(Role.name == role_name))
        ).scalar_one()
        permission_codes = (
            (
                await session.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == role_id)
                )
            )
            .scalars()
            .all()
        )
        return set(permission_codes)


async def test_seed_creates_permissions_roles_and_bindings() -> None:
    async with AsyncSessionLocal() as session:
        await ensure_default_rbac(session)

    codes = await _permission_codes()
    assert codes == set(ALL_PERMISSIONS)

    admin_codes = await _role_permission_codes(auth_constants.RoleName.ADMIN)
    user_codes = await _role_permission_codes(auth_constants.RoleName.USER)

    assert admin_codes == set(ALL_PERMISSIONS)
    assert user_codes == set()


async def test_seed_is_idempotent() -> None:
    async with AsyncSessionLocal() as session:
        await ensure_default_rbac(session)
        total_permissions = (await session.execute(select(Permission))).scalars().all()
        admin_permissions = await _role_permission_codes(auth_constants.RoleName.ADMIN)
        assert len(total_permissions) == len(ALL_PERMISSIONS)

    async with AsyncSessionLocal() as session:
        await ensure_default_rbac(session)
        total_permissions_2 = (await session.execute(select(Permission))).scalars().all()
        admin_permissions_2 = await _role_permission_codes(auth_constants.RoleName.ADMIN)

    assert len(total_permissions) == len(total_permissions_2)
    assert admin_permissions_2 == set(ALL_PERMISSIONS)
    assert admin_permissions == admin_permissions_2
