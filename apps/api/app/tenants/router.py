from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.auth.dependencies import CurrentUser, OptionalCurrentUser
from app.auth.schemas import MessageResponse
from app.core.limiter import limiter
from app.core.openapi import error_responses
from app.core.pagination import Page, Pagination
from app.core.response import ApiResponse
from app.db.session import DBSession
from app.tenants.constants import TenantRole
from app.tenants.dependencies import RequirePlatformAdmin, RequireTenantRole
from app.tenants.schemas import (
    InvitationAccepted,
    TenantCreate,
    TenantInvitationAccept,
    TenantInvitationCreate,
    TenantInvitationRead,
    TenantMembershipRead,
    TenantMemberUpdate,
    TenantRead,
    TenantUpdate,
)
from app.tenants.service import TenantService
from app.users.exceptions import UserNotFound

router = APIRouter()
invitation_router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[TenantRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePlatformAdmin())],
    summary="创建租户",
    description="平台管理员创建租户并向首位 owner 发送一次性邀请。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_409_CONFLICT
    ),
)
async def create_tenant(
    payload: TenantCreate, current_user: CurrentUser, session: DBSession
) -> ApiResponse[TenantRead]:
    tenant = await TenantService(session).create_tenant(payload, current_user)
    return ApiResponse.ok(TenantRead.model_validate(tenant))


@router.get(
    "",
    response_model=ApiResponse[Page[TenantRead]],
    summary="租户列表",
    description="平台管理员查看全部租户，普通用户仅查看自己加入的租户。",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def list_tenants(
    current_user: CurrentUser, session: DBSession, pagination: Pagination
) -> ApiResponse[Page[TenantRead]]:
    items, total = await TenantService(session).list_tenants(
        current_user, limit=pagination.limit, offset=pagination.offset
    )
    return ApiResponse.ok(
        Page(
            items=[TenantRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    )


@router.get(
    "/{tenant_id}",
    response_model=ApiResponse[TenantRead],
    dependencies=[Depends(RequireTenantRole())],
    summary="查询租户",
    description="查询当前用户可访问的租户。跨租户访问返回 404。",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def get_tenant(tenant_id: uuid.UUID, session: DBSession) -> ApiResponse[TenantRead]:
    tenant = await TenantService(session).get_tenant(tenant_id)
    return ApiResponse.ok(TenantRead.model_validate(tenant))


@router.patch(
    "/{tenant_id}",
    response_model=ApiResponse[TenantRead],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER))],
    summary="更新租户",
    description="owner 或平台管理员修改租户名称或归档状态。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def update_tenant(
    tenant_id: uuid.UUID, payload: TenantUpdate, session: DBSession
) -> ApiResponse[TenantRead]:
    tenant = await TenantService(session).update_tenant(tenant_id, payload)
    return ApiResponse.ok(TenantRead.model_validate(tenant))


@router.get(
    "/{tenant_id}/members",
    response_model=ApiResponse[Page[TenantMembershipRead]],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="租户成员列表",
    description="分页查看租户成员。",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def list_members(
    tenant_id: uuid.UUID, session: DBSession, pagination: Pagination
) -> ApiResponse[Page[TenantMembershipRead]]:
    rows, total = await TenantService(session).list_members(
        tenant_id, limit=pagination.limit, offset=pagination.offset
    )
    items = [
        TenantMembershipRead(
            tenant_id=membership.tenant_id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=TenantRole(membership.role),
            created_at=membership.created_at,
        )
        for membership, user in rows
    ]
    return ApiResponse.ok(
        Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)
    )


@router.patch(
    "/{tenant_id}/members/{user_id}",
    response_model=ApiResponse[TenantMembershipRead],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="修改成员角色",
    description="owner 管理所有租户角色；admin 只能管理普通 member。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def update_member(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: TenantMemberUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> ApiResponse[TenantMembershipRead]:
    service = TenantService(session)
    membership = await service.update_member(tenant_id, user_id, payload.role, current_user)
    user = await service.users.get_by_id(user_id)
    if user is None:
        raise UserNotFound(user_id)
    return ApiResponse.ok(
        TenantMembershipRead(
            tenant_id=tenant_id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=TenantRole(membership.role),
            created_at=membership.created_at,
        )
    )


@router.delete(
    "/{tenant_id}/members/{user_id}",
    response_model=ApiResponse[MessageResponse],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="移除租户成员",
    description="移除成员，但不允许移除租户最后一位 owner。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def remove_member(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> ApiResponse[MessageResponse]:
    await TenantService(session).remove_member(tenant_id, user_id, current_user)
    return ApiResponse.ok(MessageResponse(detail="member removed"))


@router.post(
    "/{tenant_id}/invitations",
    response_model=ApiResponse[TenantInvitationRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="邀请租户成员",
    description="owner 可邀请任意固定角色；admin 只能邀请 member。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def create_invitation(
    tenant_id: uuid.UUID,
    payload: TenantInvitationCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> ApiResponse[TenantInvitationRead]:
    invitation = await TenantService(session).invite(tenant_id, payload, current_user)
    return ApiResponse.ok(TenantInvitationRead.model_validate(invitation))


@router.get(
    "/{tenant_id}/invitations",
    response_model=ApiResponse[Page[TenantInvitationRead]],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="租户邀请列表",
    description="查看租户邀请及其接受、撤销和过期状态。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def list_invitations(
    tenant_id: uuid.UUID, session: DBSession, pagination: Pagination
) -> ApiResponse[Page[TenantInvitationRead]]:
    items, total = await TenantService(session).list_invitations(
        tenant_id, limit=pagination.limit, offset=pagination.offset
    )
    return ApiResponse.ok(
        Page(
            items=[TenantInvitationRead.model_validate(item) for item in items],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    )


@router.post(
    "/{tenant_id}/invitations/{invitation_id}/revoke",
    response_model=ApiResponse[TenantInvitationRead],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="撤销租户邀请",
    description="撤销尚未接受的邀请。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def revoke_invitation(
    tenant_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> ApiResponse[TenantInvitationRead]:
    invitation = await TenantService(session).revoke_invitation(
        tenant_id, invitation_id, current_user
    )
    return ApiResponse.ok(TenantInvitationRead.model_validate(invitation))


@invitation_router.post(
    "/accept",
    response_model=ApiResponse[InvitationAccepted],
    summary="接受租户邀请",
    description="已有用户必须使用受邀邮箱登录；新用户可随邀请设置姓名和密码。",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_409_CONFLICT,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        status.HTTP_429_TOO_MANY_REQUESTS,
    ),
)
@limiter.limit("20/minute")
async def accept_invitation(
    request: Request,
    payload: TenantInvitationAccept,
    current_user: OptionalCurrentUser,
    session: DBSession,
) -> ApiResponse[InvitationAccepted]:
    membership = await TenantService(session).accept_invitation(payload, current_user)
    return ApiResponse.ok(
        InvitationAccepted(
            tenant_id=membership.tenant_id,
            user_id=membership.user_id,
            role=TenantRole(membership.role),
        )
    )
