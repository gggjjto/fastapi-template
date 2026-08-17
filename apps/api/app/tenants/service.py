from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import RoleName
from app.auth.repository import RbacRepository
from app.auth.security import hash_password
from app.core.config import get_settings
from app.tenants.constants import TenantRole
from app.tenants.exceptions import (
    TenantInvitationAuthenticationRequired,
    TenantInvitationConflict,
    TenantInvitationInvalid,
    TenantInvitationNotFound,
    TenantMemberConflict,
    TenantMemberNotFound,
    TenantNotFound,
    TenantOwnerRequired,
    TenantSlugConflict,
)
from app.tenants.mail import send_invitation
from app.tenants.models import Tenant, TenantInvitation, TenantMembership
from app.tenants.repository import TenantRepository
from app.tenants.schemas import (
    TenantCreate,
    TenantInvitationAccept,
    TenantInvitationCreate,
    TenantUpdate,
)
from app.users.models import User
from app.users.repository import UserRepository


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tenants = TenantRepository(session)
        self.users = UserRepository(session)
        self.rbac = RbacRepository(session)
        self.settings = get_settings()

    async def create_tenant(self, payload: TenantCreate, actor: User) -> Tenant:
        if await self.tenants.get_by_slug(payload.slug):
            raise TenantSlugConflict()
        try:
            tenant = await self.tenants.create(
                name=payload.name, slug=payload.slug, created_by=actor.id
            )
            invitation, token = await self._create_invitation(
                tenant, str(payload.owner_email), TenantRole.OWNER, actor
            )
            await self.session.commit()
            await self.session.refresh(tenant)
        except IntegrityError as exc:
            await self.session.rollback()
            raise TenantSlugConflict() from exc
        await self._deliver_invitation(invitation, tenant, token)
        return tenant

    async def list_tenants(
        self, actor: User, *, limit: int, offset: int
    ) -> tuple[list[Tenant], int]:
        platform_admin = await self._is_platform_admin(actor.id)
        return await self.tenants.list_for_user(
            actor.id, include_all=platform_admin, limit=limit, offset=offset
        )

    async def update_tenant(self, tenant_id: uuid.UUID, payload: TenantUpdate) -> Tenant:
        tenant = await self._tenant(tenant_id)
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in changes.items():
            setattr(tenant, key, value)
        await self.session.commit()
        await self.session.refresh(tenant)
        return tenant

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        return await self._tenant(tenant_id)

    async def list_members(
        self, tenant_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[tuple[TenantMembership, User]], int]:
        await self._tenant(tenant_id)
        return await self.tenants.list_members(tenant_id, limit=limit, offset=offset)

    async def update_member(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: TenantRole,
        actor: User,
    ) -> TenantMembership:
        membership = await self._membership(tenant_id, user_id)
        await self._authorize_member_change(tenant_id, actor, membership, role)
        if membership.role == TenantRole.OWNER and role != TenantRole.OWNER:
            await self._require_another_owner(tenant_id)
        membership.role = role
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def remove_member(self, tenant_id: uuid.UUID, user_id: uuid.UUID, actor: User) -> None:
        membership = await self._membership(tenant_id, user_id)
        await self._authorize_member_change(tenant_id, actor, membership, None)
        if membership.role == TenantRole.OWNER:
            await self._require_another_owner(tenant_id)
        await self.tenants.delete_membership(membership)
        await self.session.commit()

    async def invite(
        self, tenant_id: uuid.UUID, payload: TenantInvitationCreate, actor: User
    ) -> TenantInvitation:
        tenant = await self.tenants.get_for_update(tenant_id)
        if tenant is None:
            raise TenantNotFound()
        await self._authorize_invitation_role(tenant_id, actor, payload.role)
        email = str(payload.email).lower()
        existing_user = await self.users.get_by_email(email)
        if existing_user and await self.tenants.membership(tenant_id, existing_user.id):
            raise TenantMemberConflict()
        invitation, token = await self._create_invitation(tenant, email, payload.role, actor)
        await self.session.commit()
        await self.session.refresh(invitation)
        await self._deliver_invitation(invitation, tenant, token)
        return invitation

    async def list_invitations(
        self, tenant_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[TenantInvitation], int]:
        await self._tenant(tenant_id)
        return await self.tenants.list_invitations(tenant_id, limit=limit, offset=offset)

    async def revoke_invitation(
        self, tenant_id: uuid.UUID, invitation_id: uuid.UUID, actor: User
    ) -> TenantInvitation:
        invitation = await self.tenants.invitation(tenant_id, invitation_id)
        if invitation is None:
            raise TenantInvitationNotFound()
        await self._authorize_invitation_role(tenant_id, actor, TenantRole(invitation.role))
        if invitation.accepted_at is not None:
            raise TenantInvitationConflict("Accepted invitation cannot be revoked")
        if invitation.revoked_at is None:
            invitation.revoked_at = datetime.now(UTC)
            await self.session.commit()
            await self.session.refresh(invitation)
        return invitation

    async def accept_invitation(
        self, payload: TenantInvitationAccept, current_user: User | None
    ) -> TenantMembership:
        invitation = await self.tenants.invitation_by_hash(self._token_hash(payload.token))
        now = datetime.now(UTC)
        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.revoked_at is not None
            or invitation.expires_at <= now
            or invitation.email.lower() != str(payload.email).lower()
        ):
            raise TenantInvitationInvalid()

        user = await self.users.get_by_email(invitation.email)
        if user is not None:
            if current_user is None or current_user.id != user.id:
                raise TenantInvitationAuthenticationRequired()
        else:
            if current_user is not None or not payload.full_name or not payload.password:
                raise TenantInvitationInvalid("New user name and password are required")
            user = await self.users.create(
                email=invitation.email,
                full_name=payload.full_name,
                hashed_password=hash_password(payload.password),
            )
            role = await self.rbac.get_role_by_name(RoleName.USER)
            if role is None:
                raise RuntimeError(f"Default role not found: {RoleName.USER}")
            await self.rbac.assign_role_to_user(user.id, role.id)

        existing = await self.tenants.membership(invitation.tenant_id, user.id)
        if existing is not None:
            raise TenantMemberConflict()
        membership = await self.tenants.add_membership(
            invitation.tenant_id, user.id, TenantRole(invitation.role)
        )
        invitation.accepted_at = now
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def _create_invitation(
        self, tenant: Tenant, email: str, role: TenantRole, actor: User
    ) -> tuple[TenantInvitation, str]:
        email = email.lower()
        if await self.tenants.active_invitation(tenant.id, email):
            raise TenantInvitationConflict("An active invitation already exists")
        token = secrets.token_urlsafe(32)
        invitation = await self.tenants.create_invitation(
            tenant_id=tenant.id,
            email=email,
            role=role,
            token_hash=self._token_hash(token),
            invited_by=actor.id,
            expires_at=datetime.now(UTC)
            + timedelta(hours=self.settings.tenant_invitation_expire_hours),
        )
        return invitation, token

    async def _deliver_invitation(
        self, invitation: TenantInvitation, tenant: Tenant, token: str
    ) -> None:
        await asyncio.to_thread(
            send_invitation,
            self.settings,
            email=invitation.email,
            tenant_name=tenant.name,
            token=token,
        )

    async def _tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.tenants.get(tenant_id)
        if tenant is None:
            raise TenantNotFound()
        return tenant

    async def _membership(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> TenantMembership:
        membership = await self.tenants.membership(tenant_id, user_id)
        if membership is None:
            raise TenantMemberNotFound()
        return membership

    async def _is_platform_admin(self, user_id: uuid.UUID) -> bool:
        return await self.rbac.user_has_role(user_id, RoleName.PLATFORM_ADMIN)

    async def _actor_role(self, tenant_id: uuid.UUID, actor: User) -> TenantRole | None:
        if await self._is_platform_admin(actor.id):
            return None
        membership = await self.tenants.membership(tenant_id, actor.id)
        if membership is None:
            raise TenantNotFound()
        return TenantRole(membership.role)

    async def _authorize_invitation_role(
        self, tenant_id: uuid.UUID, actor: User, role: TenantRole
    ) -> None:
        actor_role = await self._actor_role(tenant_id, actor)
        if actor_role is None or actor_role == TenantRole.OWNER:
            return
        if actor_role != TenantRole.ADMIN or role != TenantRole.MEMBER:
            raise TenantOwnerRequired()

    async def _authorize_member_change(
        self,
        tenant_id: uuid.UUID,
        actor: User,
        target: TenantMembership,
        new_role: TenantRole | None,
    ) -> None:
        actor_role = await self._actor_role(tenant_id, actor)
        if actor_role is None or actor_role == TenantRole.OWNER:
            return
        if (
            actor_role != TenantRole.ADMIN
            or target.role != TenantRole.MEMBER
            or new_role not in (None, TenantRole.MEMBER)
        ):
            raise TenantOwnerRequired()

    async def _require_another_owner(self, tenant_id: uuid.UUID) -> None:
        if await self.tenants.owner_count(tenant_id) <= 1:
            raise TenantMemberConflict("A tenant must keep at least one owner")

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
