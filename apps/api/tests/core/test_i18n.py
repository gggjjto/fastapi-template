from __future__ import annotations

from httpx import AsyncClient

from app.core.i18n import negotiate_locale, translate

_LOGIN = {"email": "nobody@example.com", "password": "WrongPassword1!"}


# ── unit: locale negotiation ──────────────────────────────────────────────────


async def test_negotiate_exact_match() -> None:
    assert negotiate_locale("zh-CN") == "zh-CN"


async def test_negotiate_base_language() -> None:
    assert negotiate_locale("zh") == "zh-CN"


async def test_negotiate_quality_list_picks_supported() -> None:
    assert negotiate_locale("fr-FR,zh-CN;q=0.8") == "zh-CN"


async def test_negotiate_unsupported_falls_back_to_default() -> None:
    assert negotiate_locale("fr") == "en-US"


async def test_negotiate_none_returns_default() -> None:
    assert negotiate_locale(None) == "en-US"


# ── unit: translation + fallback ──────────────────────────────────────────────


async def test_translate_known_key() -> None:
    assert translate("errors.user.not_found", "zh-CN") == "用户不存在"


async def test_translate_missing_key_returns_none() -> None:
    assert translate("errors.does.not_exist", "zh-CN") is None


async def test_translate_unknown_locale_falls_back_to_default() -> None:
    # "fr-FR" 没有目录 → 回退默认语言 en-US
    assert translate("errors.user.not_found", "fr-FR") == "User not found"


# ── integration: localized domain error message ───────────────────────────────


async def test_login_error_localized_chinese(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/token", json=_LOGIN, headers={"Accept-Language": "zh-CN"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_INVALID_CREDENTIALS"  # 错误码不翻译
    assert resp.json()["message"] == "邮箱或密码错误"


async def test_login_error_localized_english(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/token", json=_LOGIN, headers={"Accept-Language": "en-US"}
    )
    assert resp.json()["message"] == "Invalid email or password"


async def test_login_error_unsupported_locale_uses_default(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/token", json=_LOGIN, headers={"Accept-Language": "fr-FR"}
    )
    assert resp.json()["message"] == "Invalid email or password"
