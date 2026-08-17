from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import constants as auth_constants
from app.auth.models import Permission, Role, RolePermission
from app.users import constants as users_constants

# 全部权限码（resource:action）
ALL_PERMISSIONS: list[str] = [
    users_constants.Permission.READ,
    users_constants.Permission.CREATE,
    users_constants.Permission.UPDATE,
    users_constants.Permission.DELETE,
    auth_constants.Permission.ROLES_READ,
    auth_constants.Permission.ROLES_MANAGE,
]

# 默认角色 → 权限码。平台管理员拥有全部；普通用户仅通过租户成员身份授权。
ROLE_PERMISSIONS: dict[str, list[str]] = {
    auth_constants.RoleName.PLATFORM_ADMIN: ALL_PERMISSIONS,
    auth_constants.RoleName.USER: [],
}


async def ensure_default_rbac(session: AsyncSession) -> None:
    """幂等地播种权限目录与默认角色。每次启动调用，已存在则跳过。"""
    if session.get_bind().dialect.name == "postgresql":
        # 多进程同时启动时串行化参考数据播种，避免唯一约束竞争。
        await session.execute(text("SELECT pg_advisory_xact_lock(724819503)"))
    permissions = {p.code: p for p in (await session.scalars(select(Permission))).all()}
    for code in ALL_PERMISSIONS:
        if code not in permissions:
            permission = Permission(code=code)
            session.add(permission)
            permissions[code] = permission
    await session.flush()

    roles = {r.name: r for r in (await session.scalars(select(Role))).all()}
    for role_name, permission_codes in ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if role is None:
            role = Role(name=role_name)
            session.add(role)
            await session.flush()
            roles[role_name] = role

        existing_permission_ids = {
            rp.permission_id
            for rp in (
                await session.scalars(
                    select(RolePermission).where(RolePermission.role_id == role.id)
                )
            ).all()
        }
        for code in permission_codes:
            permission_id = permissions[code].id
            if permission_id not in existing_permission_ids:
                session.add(RolePermission(role_id=role.id, permission_id=permission_id))

    await session.commit()
