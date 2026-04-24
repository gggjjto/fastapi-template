from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.core.schemas import CustomModel


class UserCreate(CustomModel):
    email: EmailStr = Field(description="用户邮箱，全局唯一", examples=["user@example.com"])
    full_name: str = Field(min_length=1, max_length=255, description="用户姓名", examples=["张三"])
    password: str = Field(min_length=8, max_length=128, description="密码，8~128 位", examples=["Password123!"])


class UserRead(CustomModel):
    id: uuid.UUID = Field(description="用户唯一标识")
    email: EmailStr = Field(description="用户邮箱")
    full_name: str = Field(description="用户姓名")
    is_active: bool = Field(description="账号是否启用")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")
