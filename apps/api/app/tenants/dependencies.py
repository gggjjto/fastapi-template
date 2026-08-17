from __future__ import annotations

from uuid import UUID

from app.auth.constants import RoleName
from app.auth.dependencies import CurrentUser
from app.auth.repository import RbacRepository
from app.core.exceptions import ForbiddenError
from app.db.session import DBSession
from app.tenants.constants import TenantRole
from app.tenants.exceptions import TenantNotFound
from app.tenants.repository import TenantRepository


class RequirePlatformAdmin:
    async def __call__(self, current_user: CurrentUser, session: DBSession) -> None:
        if not await RbacRepository(session).user_has_role(
            current_user.id, RoleName.PLATFORM_ADMIN
        ):
            raise ForbiddenError("Platform administrator permission required")


class RequireTenantRole:
    def __init__(self, *roles: TenantRole) -> None:
        self.roles = set(roles)

    async def __call__(
        self,
        tenant_id: UUID,
        current_user: CurrentUser,
        session: DBSession,
    ) -> None:
        tenants = TenantRepository(session)
        if await tenants.get(tenant_id) is None:
            raise TenantNotFound()
        if await RbacRepository(session).user_has_role(current_user.id, RoleName.PLATFORM_ADMIN):
            return
        membership = await tenants.membership(tenant_id, current_user.id)
        if membership is None:
            raise TenantNotFound()
        if self.roles and membership.role not in self.roles:
            raise ForbiddenError("Tenant role permission denied")
