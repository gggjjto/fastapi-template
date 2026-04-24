from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.pagination import Page, Pagination
from app.core.response import ApiResponse
from app.db.session import DBSession
from app.users.dependencies import valid_user_id
from app.users.exceptions import UserEmailConflict
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserRead
from app.users.service import UserService

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="创建用户",
    description=(
        "创建新用户。\n\n"
        "- 邮箱全局唯一，重复注册返回 409\n"
        "- 密码长度 8~128 位，存储时使用 bcrypt 哈希，不可逆"
    ),
)
async def create_user(payload: UserCreate, session: DBSession) -> ApiResponse[UserRead]:
    try:
        user = await UserService(UserRepository(session)).create_user(payload)
    except UserEmailConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ApiResponse.ok(UserRead.model_validate(user))


@router.get(
    "",
    response_model=ApiResponse[Page[UserRead]],
    summary="用户列表",
    description=(
        "分页查询用户列表。\n\n"
        "- `limit`：每页数量，范围 1~100，默认 20\n"
        "- `offset`：跳过条数，默认 0\n"
        "- 返回体包含 `total`（总数）、`items`（当页数据）、`limit`、`offset`"
    ),
)
async def list_users(session: DBSession, pagination: Pagination) -> ApiResponse[Page[UserRead]]:
    users, total = await UserService(UserRepository(session)).list_users(
        limit=pagination.limit, offset=pagination.offset
    )
    return ApiResponse.ok(
        Page(
            items=[UserRead.model_validate(u) for u in users],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    )


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserRead],
    summary="查询用户",
    description=(
        "根据 ID 查询单个用户。\n\n"
        "- `user_id` 必须是合法的 UUID 格式\n"
        "- 用户不存在时返回 404"
    ),
)
async def get_user(user: User = Depends(valid_user_id)) -> ApiResponse[UserRead]:
    return ApiResponse.ok(UserRead.model_validate(user))
