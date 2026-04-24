from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.auth.dependencies import CurrentUser
from app.auth.exceptions import InvalidCredentials, InvalidToken
from app.auth.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.auth.service import AuthService
from app.core.limiter import limiter
from app.core.response import ApiResponse
from app.db.session import DBSession
from app.users.repository import UserRepository
from app.users.schemas import UserRead

router = APIRouter()


@router.post(
    "/token",
    response_model=ApiResponse[TokenResponse],
    summary="用户登录",
    description=(
        "用户登录，返回 access_token 和 refresh_token。\n\n"
        "- access_token 有效期较短（默认 30 分钟），用于访问受保护接口\n"
        "- refresh_token 有效期较长（默认 30 天），用于刷新 access_token\n"
        "- 同一 IP 每分钟最多请求 10 次，超出返回 429"
    ),
)
@limiter.limit("10/minute")  # 登录接口限流，防止暴力破解
async def login(
    request: Request,  # slowapi 限流需要获取客户端 IP，必须传入 request
    payload: LoginRequest,
    session: DBSession,
) -> ApiResponse[TokenResponse]:
    try:
        tokens = await AuthService(UserRepository(session)).login(payload.email, payload.password)
    except InvalidCredentials as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return ApiResponse.ok(tokens)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="刷新令牌",
    description=(
        "使用 refresh_token 获取新的 access_token 和 refresh_token。\n\n"
        "- refresh_token 只能用于此接口，不能用于访问其他受保护接口\n"
        "- token 无效或已过期时返回 401"
    ),
)
@limiter.limit("20/minute")  # 刷新接口限流
async def refresh(
    request: Request,  # slowapi 限流需要
    payload: RefreshRequest,
    session: DBSession,
) -> ApiResponse[TokenResponse]:
    try:
        tokens = await AuthService(UserRepository(session)).refresh(payload.refresh_token)
    except InvalidToken as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return ApiResponse.ok(tokens)


@router.get(
    "/me",
    response_model=ApiResponse[UserRead],
    summary="获取当前用户",
    description=(
        "获取当前登录用户的信息。\n\n"
        "- 请求头需携带 `Authorization: Bearer <access_token>`\n"
        "- token 无效或过期返回 401，账号被禁用返回 403"
    ),
)
async def get_me(current_user: CurrentUser) -> ApiResponse[UserRead]:
    return ApiResponse.ok(UserRead.model_validate(current_user))
