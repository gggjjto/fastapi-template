from __future__ import annotations

from typing import Any

import pytest

from app.core import middleware as mw
from app.core.logging import redact_sensitive
from app.core.request_context import (
    bind_user_id,
    clear_request_context,
    get_request_context,
)

# ── redaction ─────────────────────────────────────────────────────────────────


async def test_redacts_sensitive_keys_recursively() -> None:
    event = {
        "event": "http.request",
        "password": "secret-pw",
        "token": "abc",
        "authorization": "Bearer xyz",
        "nested": {"refresh_token": "r", "keep": "v"},
        "keep": "ok",
    }

    out = redact_sensitive(None, "info", event)

    assert out["password"] == "***"
    assert out["token"] == "***"
    assert out["authorization"] == "***"
    assert out["nested"]["refresh_token"] == "***"
    assert out["nested"]["keep"] == "v"  # 非敏感键保留
    assert out["keep"] == "ok"
    assert out["event"] == "http.request"


# ── request context ───────────────────────────────────────────────────────────


async def test_bind_user_id_visible_in_context() -> None:
    clear_request_context()
    bind_user_id("user-123")
    try:
        assert get_request_context().get("user_id") == "user-123"
    finally:
        clear_request_context()


# ── access log ────────────────────────────────────────────────────────────────


async def test_access_log_emitted_with_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []

    class _FakeLogger:
        def info(self, event: str, **kwargs: Any) -> None:
            captured.append((event, kwargs))

    monkeypatch.setattr(mw, "logger", _FakeLogger())

    async def app(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/x",
        "headers": [],
        "client": ("1.2.3.4", 5),
    }
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await mw.RequestIDMiddleware(app)(scope, receive, send)

    assert len(captured) == 1
    event, fields = captured[0]
    assert event == "http.request"
    assert fields["method"] == "GET"
    assert fields["path"] == "/x"
    assert fields["status_code"] == 204
    assert fields["client_ip"] == "1.2.3.4"
    assert isinstance(fields["duration_ms"], float)

    start = next(m for m in sent if m["type"] == "http.response.start")
    assert any(key == b"x-request-id" for key, _ in start["headers"])
