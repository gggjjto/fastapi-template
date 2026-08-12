from __future__ import annotations

import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.repository import RbacRepository
from app.auth.seed import ensure_default_rbac
from app.db.session import AsyncSessionLocal
from app.users.models import User
from app.users.schemas import UserCreate
from app.users.service import UserService

_USER_PAYLOAD = {"email": "demo@example.com", "full_name": "Demo User", "password": "Password123!"}
_ADMIN_PAYLOAD = {"email": "admin@example.com", "full_name": "Admin", "password": "Password123!"}


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    """注册首个用户（自动成为 admin，拥有 users:read）并返回鉴权头。"""
    await client.post("/api/v1/users", json=_ADMIN_PAYLOAD)
    resp = await client.post(
        "/api/v1/auth/token",
        json={"email": _ADMIN_PAYLOAD["email"], "password": _ADMIN_PAYLOAD["password"]},
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_user_is_public(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/users", json=_USER_PAYLOAD)

    assert create_response.status_code == 201
    assert create_response.json()["code"] == "OK"
    user_data = create_response.json()["data"]
    assert user_data["email"] == "demo@example.com"
    assert "hashed_password" not in user_data


async def test_admin_can_list_users(client: AsyncClient) -> None:
    headers = await _admin_headers(client)  # admin 是第一个、也是唯一的用户

    list_response = await client.get("/api/v1/users", headers=headers)

    assert list_response.status_code == 200
    page = list_response.json()["data"]
    assert page["total"] == 1
    assert len(page["items"]) == 1


async def test_list_users_requires_authentication(client: AsyncClient) -> None:
    await client.post("/api/v1/users", json=_USER_PAYLOAD)

    resp = await client.get("/api/v1/users")

    assert resp.status_code == 401


async def test_list_users_forbidden_without_permission(client: AsyncClient) -> None:
    await _admin_headers(client)  # 首个用户占用 admin
    # 第二个用户拿到 user 角色（无权限）
    await client.post("/api/v1/users", json=_USER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/token",
        json={"email": _USER_PAYLOAD["email"], "password": _USER_PAYLOAD["password"]},
    )
    token = login.json()["data"]["access_token"]

    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
    assert resp.json()["code"] == "AUTH_PERMISSION_DENIED"


async def test_duplicate_email_returns_409(client: AsyncClient) -> None:
    await client.post("/api/v1/users", json=_USER_PAYLOAD)
    duplicate_response = await client.post(
        "/api/v1/users",
        json={**_USER_PAYLOAD, "full_name": "Another User"},
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["code"] == "USER_EMAIL_CONFLICT"


async def test_concurrent_duplicate_email_returns_one_409(client: AsyncClient) -> None:
    responses = await asyncio.gather(
        client.post("/api/v1/users", json=_USER_PAYLOAD),
        client.post("/api/v1/users", json={**_USER_PAYLOAD, "full_name": "Race User"}),
    )

    assert sorted(resp.status_code for resp in responses) == [201, 409]
    conflict = next(resp for resp in responses if resp.status_code == 409)
    assert conflict.json()["code"] == "USER_EMAIL_CONFLICT"


async def test_concurrent_initial_users_assigns_one_admin(client: AsyncClient) -> None:
    user_a = {"email": "a@example.com", "full_name": "User A", "password": "Password123!"}
    user_b = {"email": "b@example.com", "full_name": "User B", "password": "Password123!"}

    responses = await asyncio.gather(
        client.post("/api/v1/users", json=user_a),
        client.post("/api/v1/users", json=user_b),
    )

    assert [resp.status_code for resp in responses] == [201, 201]

    access_statuses = []
    for payload in (user_a, user_b):
        login = await client.post(
            "/api/v1/auth/token",
            json={"email": payload["email"], "password": payload["password"]},
        )
        token = login.json()["data"]["access_token"]
        access = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
        access_statuses.append(access.status_code)

    assert sorted(access_statuses) == [200, 403]


async def test_role_assignment_failure_rolls_back_user(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_assign_role_to_user(self: object, user_id: object, role_id: object) -> None:
        raise RuntimeError("role assignment failed")

    async with AsyncSessionLocal() as session:
        await ensure_default_rbac(session)

    monkeypatch.setattr(RbacRepository, "assign_role_to_user", fail_assign_role_to_user)

    with pytest.raises(RuntimeError, match="role assignment failed"):
        async with AsyncSessionLocal() as session:
            await UserService(session).create_user(
                UserCreate(
                    email="rollback@example.com",
                    full_name="Rollback User",
                    password="Password123!",
                )
            )

    async with AsyncSessionLocal() as session:
        user = (
            await session.scalars(select(User).where(User.email == "rollback@example.com"))
        ).one_or_none()

    assert user is None


async def test_missing_default_role_rolls_back_user(monkeypatch: pytest.MonkeyPatch) -> None:
    async def missing_role(self: object, name: object) -> None:
        return None

    async with AsyncSessionLocal() as session:
        await ensure_default_rbac(session)

    monkeypatch.setattr(RbacRepository, "get_role_by_name", missing_role)

    with pytest.raises(RuntimeError, match="Default role not found"):
        async with AsyncSessionLocal() as session:
            await UserService(session).create_user(
                UserCreate(
                    email="missing-role@example.com",
                    full_name="Missing Role",
                    password="Password123!",
                )
            )

    async with AsyncSessionLocal() as session:
        user = (
            await session.scalars(select(User).where(User.email == "missing-role@example.com"))
        ).one_or_none()

    assert user is None


async def test_non_email_integrity_error_is_not_mapped_to_email_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def create_with_other_integrity_error(self: object, **kwargs: object) -> User:
        raise IntegrityError("insert", {}, Exception("uq_other_table_column"))

    async with AsyncSessionLocal() as session:
        await ensure_default_rbac(session)

    monkeypatch.setattr(
        "app.users.repository.UserRepository.create",
        create_with_other_integrity_error,
    )

    with pytest.raises(IntegrityError, match="uq_other_table_column"):
        async with AsyncSessionLocal() as session:
            await UserService(session).create_user(
                UserCreate(
                    email="integrity@example.com",
                    full_name="Integrity User",
                    password="Password123!",
                )
            )


async def test_get_user_by_id(client: AsyncClient) -> None:
    headers = await _admin_headers(client)
    create_response = await client.post("/api/v1/users", json=_USER_PAYLOAD)
    user_id = create_response.json()["data"]["id"]

    get_response = await client.get(f"/api/v1/users/{user_id}", headers=headers)

    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == user_id


async def test_get_nonexistent_user_returns_404(client: AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await client.get(f"/api/v1/users/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"


async def test_validation_error_format(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "full_name": "", "password": "short"},
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0


async def test_list_users_pagination_slicing(client: AsyncClient) -> None:
    headers = await _admin_headers(client)  # user[0]
    for i in range(2):
        await client.post(
            "/api/v1/users",
            json={
                "email": f"user{i}@example.com",
                "full_name": f"User {i}",
                "password": "Password123!",
            },
        )

    resp = await client.get("/api/v1/users", params={"limit": 2, "offset": 1}, headers=headers)

    assert resp.status_code == 200
    page = resp.json()["data"]
    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert page["limit"] == 2
    assert page["offset"] == 1


async def test_list_users_empty_page(client: AsyncClient) -> None:
    headers = await _admin_headers(client)

    resp = await client.get("/api/v1/users", params={"offset": 10}, headers=headers)

    assert resp.status_code == 200
    page = resp.json()["data"]
    assert page["total"] == 1
    assert page["items"] == []


async def test_list_invalid_pagination_params(client: AsyncClient) -> None:
    headers = await _admin_headers(client)
    for params in [{"limit": 0}, {"limit": 101}, {"offset": -1}]:
        resp = await client.get("/api/v1/users", params=params, headers=headers)
        assert resp.status_code == 422, f"expected 422 for params={params}"
