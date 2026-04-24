from __future__ import annotations

import uuid

from httpx import AsyncClient

_USER_PAYLOAD = {"email": "demo@example.com", "full_name": "Demo User", "password": "Password123!"}


async def test_create_and_list_users(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/users", json=_USER_PAYLOAD)
    list_response = await client.get("/api/v1/users")

    assert create_response.status_code == 201
    assert create_response.json()["code"] == 200
    user_data = create_response.json()["data"]
    assert user_data["email"] == "demo@example.com"
    assert "hashed_password" not in user_data

    assert list_response.status_code == 200
    page = list_response.json()["data"]
    assert page["total"] == 1
    assert len(page["items"]) == 1


async def test_duplicate_email_returns_409(client: AsyncClient) -> None:
    await client.post("/api/v1/users", json=_USER_PAYLOAD)
    duplicate_response = await client.post(
        "/api/v1/users",
        json={**_USER_PAYLOAD, "full_name": "Another User"},
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["code"] == 409


async def test_get_user_by_id(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/users", json=_USER_PAYLOAD)
    user_id = create_response.json()["data"]["id"]

    get_response = await client.get(f"/api/v1/users/{user_id}")

    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == user_id


async def test_get_nonexistent_user_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == 404


async def test_validation_error_format(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={"email": "not-an-email", "full_name": "", "password": "short"},
    )

    assert response.status_code == 422
    data = response.json()
    assert data["code"] == 422
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
