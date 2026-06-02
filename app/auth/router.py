from __future__ import annotations

from fastapi import APIRouter, Request

from app.auth.dependencies import CurrentUser
from app.auth.schemas import LoginRequest, MessageResponse, RefreshRequest, TokenResponse
from app.auth.service import AuthService
from app.core.limiter import limiter
from app.core.response import ApiResponse
from app.db.session import DBSession
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
    tokens = await AuthService(session).login(
        payload.email,
        payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
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
    tokens = await AuthService(session).refresh(payload.refresh_token)
    return ApiResponse.ok(tokens)


@router.post(
    "/logout",
    response_model=ApiResponse[MessageResponse],
    summary="登出当前会话",
    description=(
        "撤销 refresh_token 对应的会话。\n\n"
        "- 撤销后该 refresh_token 无法再刷新（已签发的 access_token 在到期前仍有效）\n"
        "- 即使会话不存在或已撤销也返回成功，避免信息泄露"
    ),
)
async def logout(payload: RefreshRequest, session: DBSession) -> ApiResponse[MessageResponse]:
    await AuthService(session).logout(payload.refresh_token)
    return ApiResponse.ok(MessageResponse(detail="logged out"))


@router.post(
    "/logout-all",
    response_model=ApiResponse[MessageResponse],
    summary="登出全部会话",
    description=(
        "撤销当前用户的所有会话。\n\n"
        "- 请求头需携带 `Authorization: Bearer <access_token>`\n"
        "- 撤销后所有 refresh_token 均失效，常用于密码泄露后强制下线"
    ),
)
async def logout_all(current_user: CurrentUser, session: DBSession) -> ApiResponse[MessageResponse]:
    await AuthService(session).logout_all(current_user.id)
    return ApiResponse.ok(MessageResponse(detail="all sessions revoked"))


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
