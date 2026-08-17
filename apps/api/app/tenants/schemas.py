from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.auth.schemas import BcryptPassword
from app.core.schemas import CustomModel
from app.tenants.constants import TenantRole, TenantStatus

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantCreate(CustomModel):
    name: str = Field(min_length=1, max_length=255, description="租户名称", examples=["Acme"])
    slug: str = Field(
        min_length=2,
        max_length=63,
        description="租户 URL 标识",
        examples=["acme"],
    )
    owner_email: EmailStr = Field(description="首位 owner 邮箱", examples=["owner@example.com"])

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        value = value.lower()
        if not _SLUG_PATTERN.fullmatch(value):
            raise ValueError("slug must contain lowercase letters, numbers, and single hyphens")
        return value


class TenantUpdate(CustomModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="租户名称", examples=["Acme"]
    )
    status: TenantStatus | None = Field(
        default=None, description="租户状态", examples=[TenantStatus.ACTIVE]
    )


class TenantRead(CustomModel):
    id: uuid.UUID = Field(description="租户标识", examples=["8d67da52-0503-4a77-a080-c973533583b3"])
    name: str = Field(description="租户名称", examples=["Acme"])
    slug: str = Field(description="租户 URL 标识", examples=["acme"])
    status: TenantStatus = Field(description="租户状态", examples=[TenantStatus.ACTIVE])
    created_by: uuid.UUID | None = Field(
        description="创建者标识", examples=["8d67da52-0503-4a77-a080-c973533583b3"]
    )
    created_at: datetime = Field(description="创建时间", examples=["2026-01-01T00:00:00Z"])
    updated_at: datetime = Field(description="更新时间", examples=["2026-01-01T00:00:00Z"])


class TenantMembershipRead(CustomModel):
    tenant_id: uuid.UUID = Field(
        description="租户标识", examples=["8d67da52-0503-4a77-a080-c973533583b3"]
    )
    user_id: uuid.UUID = Field(
        description="用户标识", examples=["8d67da52-0503-4a77-a080-c973533583b3"]
    )
    email: EmailStr = Field(description="成员邮箱", examples=["member@example.com"])
    full_name: str = Field(description="成员姓名", examples=["Member"])
    role: TenantRole = Field(description="租户角色", examples=[TenantRole.MEMBER])
    created_at: datetime = Field(description="加入时间", examples=["2026-01-01T00:00:00Z"])


class TenantMemberUpdate(CustomModel):
    role: TenantRole = Field(description="新租户角色", examples=[TenantRole.ADMIN])


class TenantInvitationCreate(CustomModel):
    email: EmailStr = Field(description="受邀邮箱", examples=["member@example.com"])
    role: TenantRole = Field(
        default=TenantRole.MEMBER, description="受邀角色", examples=[TenantRole.MEMBER]
    )


class TenantInvitationRead(CustomModel):
    id: uuid.UUID = Field(description="邀请标识", examples=["8d67da52-0503-4a77-a080-c973533583b3"])
    tenant_id: uuid.UUID = Field(
        description="租户标识", examples=["8d67da52-0503-4a77-a080-c973533583b3"]
    )
    email: EmailStr = Field(description="受邀邮箱", examples=["member@example.com"])
    role: TenantRole = Field(description="受邀角色", examples=[TenantRole.MEMBER])
    expires_at: datetime = Field(description="过期时间", examples=["2026-01-04T00:00:00Z"])
    accepted_at: datetime | None = Field(
        default=None, description="接受时间", examples=["2026-01-01T01:00:00Z"]
    )
    revoked_at: datetime | None = Field(
        default=None, description="撤销时间", examples=["2026-01-01T01:00:00Z"]
    )
    created_at: datetime = Field(description="创建时间", examples=["2026-01-01T00:00:00Z"])


class TenantInvitationAccept(CustomModel):
    token: str = Field(
        min_length=20, description="邀请邮件中的一次性 token", examples=["invite-token"]
    )
    email: EmailStr = Field(description="受邀邮箱", examples=["member@example.com"])
    full_name: str | None = Field(
        default=None, min_length=1, max_length=255, description="新用户姓名", examples=["Member"]
    )
    password: BcryptPassword | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="新用户密码",
        examples=["Password123!"],
    )


class InvitationAccepted(CustomModel):
    tenant_id: uuid.UUID = Field(
        description="已加入租户", examples=["8d67da52-0503-4a77-a080-c973533583b3"]
    )
    user_id: uuid.UUID = Field(
        description="用户标识", examples=["8d67da52-0503-4a77-a080-c973533583b3"]
    )
    role: TenantRole = Field(description="租户角色", examples=[TenantRole.MEMBER])
