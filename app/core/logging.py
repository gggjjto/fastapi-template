from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

# 永不写入日志的敏感字段（大小写不敏感匹配）
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {"password", "token", "access_token", "refresh_token", "authorization", "cookie", "secret"}
)
_REDACTED = "***"


def _redact_in_place(data: MutableMapping[str, Any]) -> None:
    for key, value in data.items():
        if isinstance(key, str) and key.lower() in _SENSITIVE_KEYS:
            data[key] = _REDACTED
        elif isinstance(value, MutableMapping):
            _redact_in_place(value)


def redact_sensitive(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """structlog 处理器：递归遮蔽敏感键的值，防止密码/令牌等泄露到日志。"""
    _redact_in_place(event_dict)
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        redact_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.types.Processor
    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO), format="%(message)s"
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)
