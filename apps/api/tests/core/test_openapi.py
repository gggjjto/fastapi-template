from __future__ import annotations

import os
import subprocess
import sys

from app.core.config import get_settings
from app.main import app

_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
_settings = get_settings()


def _api_path(path: str) -> str:
    return f"{_settings.api_v1_prefix}{path}"


def _schema() -> dict:
    return app.openapi()


def test_openapi_exposes_bearer_security_scheme() -> None:
    schema = _schema()
    assert "OAuth2PasswordBearer" in schema["components"]["securitySchemes"]


def test_api_prefix_drives_routes_and_oauth_token_url() -> None:
    schema = _schema()
    token_path = _api_path("/auth/token")
    assert token_path in schema["paths"]
    assert (
        schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"][
            "tokenUrl"
        ]
        == token_path
    )


def test_custom_api_prefix_drives_routes_and_oauth_token_url() -> None:
    code = """
from app.main import app

schema = app.openapi()
token_path = "/custom/auth/token"
assert token_path in schema["paths"]
assert "/api/v1/auth/token" not in schema["paths"]
assert (
    schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"][
        "tokenUrl"
    ]
    == token_path
)
"""
    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        env={**os.environ, "APP_API_V1_PREFIX": "/custom"},
        text=True,
    )


def test_protected_route_declares_security() -> None:
    schema = _schema()
    assert "security" in schema["paths"][_api_path("/auth/me")]["get"]


def test_error_envelope_schema_is_reused() -> None:
    schema = _schema()
    assert "ErrorResponse" in schema["components"]["schemas"]
    get_user = schema["paths"][_api_path("/users/{user_id}")]["get"]
    assert "404" in get_user["responses"]
    assert "401" in get_user["responses"]


def test_every_operation_has_summary_and_tags() -> None:
    schema = _schema()
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in _HTTP_METHODS:
                continue
            assert operation.get("summary"), f"{method.upper()} {path} missing summary"
            assert operation.get("tags"), f"{method.upper()} {path} missing tags"
