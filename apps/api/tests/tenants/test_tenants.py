from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.auth.bootstrap import bootstrap_platform_admin
from app.db.session import AsyncSessionLocal
from app.tenants.constants import TenantRole
from app.tenants.models import TenantInvitation, TenantMembership
from app.users.models import User

ADMIN = {
    "email": "platform@example.com",
    "full_name": "Platform Admin",
    "password": "Password123!",
}


async def _headers(client: AsyncClient, payload: dict[str, str]) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/token",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def _platform_headers(client: AsyncClient) -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        await bootstrap_platform_admin(session, **ADMIN)
    return await _headers(client, ADMIN)


async def test_public_signup_never_becomes_platform_admin(client: AsyncClient) -> None:
    user = {
        "email": "first@example.com",
        "full_name": "First",
        "password": "Password123!",
    }
    assert (await client.post("/api/v1/users", json=user)).status_code == 201

    response = await client.get("/api/v1/users", headers=await _headers(client, user))

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_PERMISSION_DENIED"


async def test_bootstrap_platform_admin_is_one_time(client: AsyncClient) -> None:
    headers = await _platform_headers(client)
    assert (await client.get("/api/v1/users", headers=headers)).status_code == 200

    async with AsyncSessionLocal() as session:
        with pytest.raises(RuntimeError, match="already exists"):
            await bootstrap_platform_admin(
                session,
                email="second-platform@example.com",
                full_name="Second",
                password="Password123!",
            )


async def test_concurrent_bootstrap_creates_only_one_platform_admin(
    client: AsyncClient,
) -> None:
    async def bootstrap(email: str) -> str:
        try:
            async with AsyncSessionLocal() as session:
                await bootstrap_platform_admin(
                    session,
                    email=email,
                    full_name="Platform Admin",
                    password="Password123!",
                )
        except RuntimeError:
            return "conflict"
        return "created"

    results = await asyncio.gather(
        bootstrap("platform-a@example.com"), bootstrap("platform-b@example.com")
    )

    assert sorted(results) == ["conflict", "created"]


async def test_create_tenant_and_accept_owner_invitation(
    client: AsyncClient, monkeypatch: Any
) -> None:
    sent: dict[str, str] = {}

    def capture_invitation(settings: object, *, email: str, tenant_name: str, token: str) -> None:
        sent.update(email=email, tenant_name=tenant_name, token=token)

    monkeypatch.setattr("app.tenants.service.send_invitation", capture_invitation)
    response = await client.post(
        "/api/v1/tenants",
        headers=await _platform_headers(client),
        json={"name": "Acme", "slug": "acme", "owner_email": "owner@example.com"},
    )

    assert response.status_code == 201
    tenant_id = response.json()["data"]["id"]
    assert sent["email"] == "owner@example.com"
    accepted = await client.post(
        "/api/v1/tenant-invitations/accept",
        json={
            "token": sent["token"],
            "email": "owner@example.com",
            "full_name": "Owner",
            "password": "Password123!",
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["tenant_id"] == tenant_id
    assert accepted.json()["data"]["role"] == "owner"

    owner = {"email": "owner@example.com", "password": "Password123!"}
    members = await client.get(
        f"/api/v1/tenants/{tenant_id}/members", headers=await _headers(client, owner)
    )
    assert members.status_code == 200
    assert members.json()["data"]["items"][0]["role"] == "owner"


async def test_existing_user_must_login_to_accept_invitation(
    client: AsyncClient, monkeypatch: Any
) -> None:
    sent: dict[str, str] = {}

    def capture(settings: object, *, email: str, tenant_name: str, token: str) -> None:
        sent["token"] = token

    monkeypatch.setattr("app.tenants.service.send_invitation", capture)
    member = {
        "email": "member@example.com",
        "full_name": "Member",
        "password": "Password123!",
    }
    await client.post("/api/v1/users", json=member)
    created = await client.post(
        "/api/v1/tenants",
        headers=await _platform_headers(client),
        json={"name": "Acme", "slug": "acme", "owner_email": member["email"]},
    )
    payload = {"token": sent["token"], "email": member["email"]}

    unauthenticated = await client.post("/api/v1/tenant-invitations/accept", json=payload)
    authenticated = await client.post(
        "/api/v1/tenant-invitations/accept",
        json=payload,
        headers=await _headers(client, member),
    )

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["code"] == "TENANT_INVITATION_AUTH_REQUIRED"
    assert authenticated.status_code == 200
    assert authenticated.json()["data"]["tenant_id"] == created.json()["data"]["id"]


async def test_cross_tenant_access_returns_404(client: AsyncClient, monkeypatch: Any) -> None:
    monkeypatch.setattr("app.tenants.service.send_invitation", lambda *args, **kwargs: None)
    created = await client.post(
        "/api/v1/tenants",
        headers=await _platform_headers(client),
        json={"name": "Acme", "slug": "acme", "owner_email": "owner@example.com"},
    )
    outsider = {
        "email": "outsider@example.com",
        "full_name": "Outsider",
        "password": "Password123!",
    }
    await client.post("/api/v1/users", json=outsider)

    response = await client.get(
        f"/api/v1/tenants/{created.json()['data']['id']}",
        headers=await _headers(client, outsider),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "TENANT_NOT_FOUND"


async def test_invitation_rejects_wrong_email_and_reuse(
    client: AsyncClient, monkeypatch: Any
) -> None:
    sent: dict[str, str] = {}

    def capture(settings: object, *, email: str, tenant_name: str, token: str) -> None:
        sent["token"] = token

    monkeypatch.setattr("app.tenants.service.send_invitation", capture)
    await client.post(
        "/api/v1/tenants",
        headers=await _platform_headers(client),
        json={"name": "Acme", "slug": "acme", "owner_email": "owner@example.com"},
    )
    wrong = await client.post(
        "/api/v1/tenant-invitations/accept",
        json={
            "token": sent["token"],
            "email": "wrong@example.com",
            "full_name": "Wrong",
            "password": "Password123!",
        },
    )
    payload = {
        "token": sent["token"],
        "email": "owner@example.com",
        "full_name": "Owner",
        "password": "Password123!",
    }
    accepted = await client.post("/api/v1/tenant-invitations/accept", json=payload)
    reused = await client.post("/api/v1/tenant-invitations/accept", json=payload)

    assert wrong.status_code == 403
    assert accepted.status_code == 200
    assert reused.status_code == 403
    assert reused.json()["code"] == "TENANT_INVITATION_INVALID"


async def test_concurrent_duplicate_invitation_returns_one_conflict(
    client: AsyncClient, monkeypatch: Any
) -> None:
    monkeypatch.setattr("app.tenants.service.send_invitation", lambda *args, **kwargs: None)
    headers = await _platform_headers(client)
    created = await client.post(
        "/api/v1/tenants",
        headers=headers,
        json={"name": "Acme", "slug": "acme", "owner_email": "owner@example.com"},
    )
    tenant_id = created.json()["data"]["id"]

    responses = await asyncio.gather(
        client.post(
            f"/api/v1/tenants/{tenant_id}/invitations",
            headers=headers,
            json={"email": "member@example.com", "role": "member"},
        ),
        client.post(
            f"/api/v1/tenants/{tenant_id}/invitations",
            headers=headers,
            json={"email": "member@example.com", "role": "member"},
        ),
    )

    assert sorted(response.status_code for response in responses) == [201, 409]


async def test_expired_and_revoked_invitations_are_rejected(
    client: AsyncClient, monkeypatch: Any
) -> None:
    sent: dict[str, str] = {}

    def capture(settings: object, *, email: str, tenant_name: str, token: str) -> None:
        sent[email] = token

    monkeypatch.setattr("app.tenants.service.send_invitation", capture)
    headers = await _platform_headers(client)
    created = await client.post(
        "/api/v1/tenants",
        headers=headers,
        json={"name": "Acme", "slug": "acme", "owner_email": "expired@example.com"},
    )
    tenant_id = created.json()["data"]["id"]
    async with AsyncSessionLocal() as session:
        invitation = await session.scalar(
            select(TenantInvitation).where(TenantInvitation.email == "expired@example.com")
        )
        assert invitation is not None
        invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    expired = await client.post(
        "/api/v1/tenant-invitations/accept",
        json={
            "token": sent["expired@example.com"],
            "email": "expired@example.com",
            "full_name": "Expired",
            "password": "Password123!",
        },
    )

    invited = await client.post(
        f"/api/v1/tenants/{tenant_id}/invitations",
        headers=headers,
        json={"email": "revoked@example.com", "role": "member"},
    )
    invitation_id = invited.json()["data"]["id"]
    revoked = await client.post(
        f"/api/v1/tenants/{tenant_id}/invitations/{invitation_id}/revoke",
        headers=headers,
    )
    rejected = await client.post(
        "/api/v1/tenant-invitations/accept",
        json={
            "token": sent["revoked@example.com"],
            "email": "revoked@example.com",
            "full_name": "Revoked",
            "password": "Password123!",
        },
    )

    assert expired.status_code == 403
    assert revoked.status_code == 200
    assert rejected.status_code == 403


async def test_tenant_role_matrix(client: AsyncClient, monkeypatch: Any) -> None:
    monkeypatch.setattr("app.tenants.service.send_invitation", lambda *args, **kwargs: None)
    platform_headers = await _platform_headers(client)
    created = await client.post(
        "/api/v1/tenants",
        headers=platform_headers,
        json={"name": "Acme", "slug": "acme", "owner_email": "pending@example.com"},
    )
    tenant_id = created.json()["data"]["id"]
    tenant_uuid = uuid.UUID(tenant_id)
    users = [
        {"email": "owner@example.com", "full_name": "Owner", "password": "Password123!"},
        {"email": "admin@example.com", "full_name": "Admin", "password": "Password123!"},
        {"email": "member@example.com", "full_name": "Member", "password": "Password123!"},
    ]
    for payload in users:
        await client.post("/api/v1/users", json=payload)
    async with AsyncSessionLocal() as session:
        db_users = list(
            (
                await session.scalars(
                    select(User).where(User.email.in_([item["email"] for item in users]))
                )
            ).all()
        )
        role_by_email = {
            "owner@example.com": TenantRole.OWNER,
            "admin@example.com": TenantRole.ADMIN,
            "member@example.com": TenantRole.MEMBER,
        }
        for user in db_users:
            session.add(
                TenantMembership(
                    tenant_id=tenant_uuid,
                    user_id=user.id,
                    role=role_by_email[user.email],
                )
            )
        await session.commit()

    owner_headers = await _headers(client, users[0])
    admin_headers = await _headers(client, users[1])
    member_headers = await _headers(client, users[2])
    assert (
        await client.patch(
            f"/api/v1/tenants/{tenant_id}", headers=owner_headers, json={"name": "Renamed"}
        )
    ).status_code == 200
    assert (
        await client.post(
            f"/api/v1/tenants/{tenant_id}/invitations",
            headers=admin_headers,
            json={"email": "new@example.com", "role": "member"},
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/v1/tenants/{tenant_id}/invitations",
            headers=admin_headers,
            json={"email": "owner2@example.com", "role": "owner"},
        )
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/tenants/{tenant_id}", headers=member_headers, json={"name": "Denied"}
        )
    ).status_code == 403
