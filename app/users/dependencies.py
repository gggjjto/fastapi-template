from __future__ import annotations

import uuid

from app.db.session import DBSession
from app.users.exceptions import UserNotFound
from app.users.models import User
from app.users.repository import UserRepository


async def valid_user_id(user_id: uuid.UUID, session: DBSession) -> User:
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise UserNotFound(user_id)
    return user
