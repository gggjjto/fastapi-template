from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

SUPPORTED_LOCALES: tuple[str, ...] = ("en-US", "zh-CN")

_LOCALES_DIR = Path(__file__).resolve().parents[2] / "locales"


def _load_catalogs() -> dict[str, dict[str, str]]:
    catalogs: dict[str, dict[str, str]] = {}
    for locale in SUPPORTED_LOCALES:
        path = _LOCALES_DIR / f"{locale}.json"
        catalogs[locale] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return catalogs


_CATALOGS = _load_catalogs()


def _match(tag: str) -> str | None:
    tag = tag.lower()
    for locale in SUPPORTED_LOCALES:
        if locale.lower() == tag:
            return locale
    base = tag.split("-")[0]
    for locale in SUPPORTED_LOCALES:
        if locale.lower().split("-")[0] == base:
            return locale
    return None


def negotiate_locale(accept_language: str | None) -> str:
    """按 Accept-Language 协商语言；无匹配时回退到默认语言。"""
    if accept_language:
        for part in accept_language.split(","):
            tag = part.split(";")[0].strip()
            if tag:
                matched = _match(tag)
                if matched is not None:
                    return matched
    return settings.default_locale


def translate(message_key: str, locale: str, params: dict[str, object] | None = None) -> str | None:
    """翻译 message_key；缺失时回退默认语言，仍缺失返回 None。"""
    template = _CATALOGS.get(locale, {}).get(message_key)
    if template is None and locale != settings.default_locale:
        template = _CATALOGS.get(settings.default_locale, {}).get(message_key)
    if template is None:
        return None
    if params:
        try:
            return template.format(**params)
        except (KeyError, IndexError):
            return template
    return template
