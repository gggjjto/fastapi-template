from __future__ import annotations

import uuid

from httpx import AsyncClient

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
