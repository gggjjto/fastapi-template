from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.core.schemas import CustomModel


class UserCreate(CustomModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserRead(CustomModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
