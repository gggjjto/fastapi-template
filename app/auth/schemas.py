from __future__ import annotations

from pydantic import EmailStr, Field

from app.core.schemas import CustomModel


class LoginRequest(CustomModel):
    email: EmailStr = Field(description="用户邮箱", examples=["user@example.com"])
    password: str = Field(
        min_length=8, max_length=128, description="用户密码", examples=["Password123!"]
    )


class RefreshRequest(CustomModel):
    refresh_token: str = Field(min_length=1, description="登录时颁发的 refresh_token")


class TokenResponse(CustomModel):
    access_token: str = Field(description="短期访问令牌，用于调用受保护接口")
    refresh_token: str = Field(description="长期刷新令牌，用于换取新的 access_token")
    token_type: str = Field(default="bearer", description="令牌类型，固定为 bearer")
