from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenants.constants import TenantRole
from app.tenants.models import Tenant, TenantInvitation, TenantMembership
from app.users.models import User


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, tenant_id: uuid.UUID) -> Tenant | None:
        return await self.session.get(Tenant, tenant_id)

    async def get_for_update(self, tenant_id: uuid.UUID) -> Tenant | None:
        return await self.session.scalar(
            select(Tenant).where(Tenant.id == tenant_id).with_for_update()
        )

    async def get_by_slug(self, slug: str) -> Tenant | None:
        return await self.session.scalar(select(Tenant).where(Tenant.slug == slug))

    async def create(self, *, name: str, slug: str, created_by: uuid.UUID) -> Tenant:
        tenant = Tenant(name=name, slug=slug, created_by=created_by)
        self.session.add(tenant)
        await self.session.flush()
        return tenant

    async def list_for_user(
        self, user_id: uuid.UUID, *, include_all: bool, limit: int, offset: int
    ) -> tuple[list[Tenant], int]:
        stmt = select(Tenant)
        if not include_all:
            stmt = stmt.join(TenantMembership).where(TenantMembership.user_id == user_id)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.scalar(count_stmt)) or 0)
        tenants = list(
            (
                await self.session.scalars(
                    stmt.order_by(Tenant.created_at).offset(offset).limit(limit)
                )
            ).all()
        )
        return tenants, total

    async def membership(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> TenantMembership | None:
        return await self.session.get(TenantMembership, (tenant_id, user_id))

    async def add_membership(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, role: TenantRole
    ) -> TenantMembership:
        membership = TenantMembership(tenant_id=tenant_id, user_id=user_id, role=role)
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def list_members(
        self, tenant_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[tuple[TenantMembership, User]], int]:
        base = (
            select(TenantMembership, User)
            .join(User, User.id == TenantMembership.user_id)
            .where(TenantMembership.tenant_id == tenant_id)
        )
        total = int(
            (await self.session.scalar(select(func.count()).select_from(base.subquery()))) or 0
        )
        rows = list(
            (
                await self.session.execute(
                    base.order_by(TenantMembership.created_at).offset(offset).limit(limit)
                )
            )
            .tuples()
            .all()
        )
        return rows, total

    async def owner_count(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(TenantMembership)
            .where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.role == TenantRole.OWNER,
            )
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def delete_membership(self, membership: TenantMembership) -> None:
        await self.session.delete(membership)
        await self.session.flush()

    async def active_invitation(self, tenant_id: uuid.UUID, email: str) -> TenantInvitation | None:
        now = datetime.now(UTC)
        stmt = select(TenantInvitation).where(
            TenantInvitation.tenant_id == tenant_id,
            TenantInvitation.email == email,
            TenantInvitation.accepted_at.is_(None),
            TenantInvitation.revoked_at.is_(None),
            TenantInvitation.expires_at > now,
        )
        return await self.session.scalar(stmt)

    async def create_invitation(
        self,
        *,
        tenant_id: uuid.UUID,
        email: str,
        role: TenantRole,
        token_hash: str,
        invited_by: uuid.UUID,
        expires_at: datetime,
    ) -> TenantInvitation:
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            email=email,
            role=role,
            token_hash=token_hash,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.session.add(invitation)
        await self.session.flush()
        return invitation

    async def invitation_by_hash(self, token_hash: str) -> TenantInvitation | None:
        return await self.session.scalar(
            select(TenantInvitation)
            .where(TenantInvitation.token_hash == token_hash)
            .with_for_update()
        )

    async def invitation(
        self, tenant_id: uuid.UUID, invitation_id: uuid.UUID
    ) -> TenantInvitation | None:
        return await self.session.scalar(
            select(TenantInvitation).where(
                TenantInvitation.id == invitation_id,
                TenantInvitation.tenant_id == tenant_id,
            )
        )

    async def list_invitations(
        self, tenant_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[TenantInvitation], int]:
        where = TenantInvitation.tenant_id == tenant_id
        total = int(
            (
                await self.session.scalar(
                    select(func.count()).select_from(TenantInvitation).where(where)
                )
            )
            or 0
        )
        items = list(
            (
                await self.session.scalars(
                    select(TenantInvitation)
                    .where(where)
                    .order_by(TenantInvitation.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )
        return items, total
