from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.auth.schemas import LoginRequest
from app.auth.security import hash_password, verify_password
from app.users.schemas import UserCreate


def test_password_schemas_share_bcrypt_utf8_byte_limit() -> None:
    valid_ascii = "a" * 72
    too_long_ascii = "a" * 73
    valid_multibyte = "密" * 24
    too_long_multibyte = "密" * 25

    UserCreate(email="user@example.com", full_name="User", password=valid_ascii)
    LoginRequest(email="user@example.com", password=valid_ascii)
    UserCreate(email="user@example.com", full_name="User", password=valid_multibyte)
    LoginRequest(email="user@example.com", password=valid_multibyte)

    for schema, payload in (
        (UserCreate, {"email": "user@example.com", "full_name": "User"}),
        (LoginRequest, {"email": "user@example.com"}),
    ):
        with pytest.raises(ValidationError):
            schema(**payload, password=too_long_ascii)

        with pytest.raises(ValidationError):
            schema(**payload, password=too_long_multibyte)


def test_verify_password_returns_false_for_oversized_input() -> None:
    password = "a" * 72
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("a" * 73, hashed) is False
