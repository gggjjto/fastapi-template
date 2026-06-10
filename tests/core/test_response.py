from __future__ import annotations

from app.core.response import ApiResponse


def test_api_response_error_payload() -> None:
    payload = ApiResponse.error("BAD", "Oops", data={"detail": "x"}, request_id="req-1")

    assert payload.code == "BAD"
    assert payload.message == "Oops"
    assert payload.data == {"detail": "x"}
    assert payload.request_id == "req-1"
