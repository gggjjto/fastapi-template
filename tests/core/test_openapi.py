from __future__ import annotations

from httpx import AsyncClient

_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


async def _schema(client: AsyncClient) -> dict:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json()


async def test_openapi_exposes_bearer_security_scheme(client: AsyncClient) -> None:
    schema = await _schema(client)
    assert "OAuth2PasswordBearer" in schema["components"]["securitySchemes"]


async def test_protected_route_declares_security(client: AsyncClient) -> None:
    schema = await _schema(client)
    assert "security" in schema["paths"]["/api/v1/auth/me"]["get"]


async def test_error_envelope_schema_is_reused(client: AsyncClient) -> None:
    schema = await _schema(client)
    assert "ErrorResponse" in schema["components"]["schemas"]
    get_user = schema["paths"]["/api/v1/users/{user_id}"]["get"]
    assert "404" in get_user["responses"]
    assert "401" in get_user["responses"]


async def test_every_operation_has_summary_and_tags(client: AsyncClient) -> None:
    schema = await _schema(client)
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in _HTTP_METHODS:
                continue
            assert operation.get("summary"), f"{method.upper()} {path} missing summary"
            assert operation.get("tags"), f"{method.upper()} {path} missing tags"
