from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field

from app.auth.security import validate_bcrypt_password_length
from app.core.schemas import CustomModel

BcryptPassword = Annotated[str, AfterValidator(validate_bcrypt_password_length)]


class LoginRequest(CustomModel):
    email: EmailStr = Field(description="用户邮箱", examples=["user@example.com"])
    password: BcryptPassword = Field(
        min_length=8,
        max_length=128,
        description="用户密码，最多 72 个 UTF-8 字节",
        examples=["Password123!"],
    )


class RefreshRequest(CustomModel):
    refresh_token: str = Field(min_length=1, description="登录时颁发的 refresh_token")


class MessageResponse(CustomModel):
    detail: str = Field(description="操作结果说明", examples=["logged out"])


class TokenResponse(CustomModel):
    access_token: str = Field(description="短期访问令牌，用于调用受保护接口")
    refresh_token: str = Field(description="长期刷新令牌，用于换取新的 access_token")
    token_type: str = Field(default="bearer", description="令牌类型，固定为 bearer")
