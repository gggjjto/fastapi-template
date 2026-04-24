from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.db.session import DBSession
from app.users.models import User
from app.users.repository import UserRepository


async def valid_user_id(user_id: uuid.UUID, session: DBSession) -> User:
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
