from __future__ import annotations

import logging


def init_sentry(dsn: str, env: str) -> None:
    """
    初始化 Sentry SDK。dsn 为空时直接返回，不产生任何副作用。

    启用的集成：
    - StarletteIntegration / FastApiIntegration：自动捕获请求上下文
    - SqlalchemyIntegration：将数据库查询记录为 breadcrumb
    - LoggingIntegration：将 structlog → stdlib logging → Sentry 打通，
      ERROR 级别及以上的日志自动上报为 Sentry event，业务代码无需改动

    使用方式：在 .env 中设置 APP_SENTRY_DSN；本地开发留空即可。
    """
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=env,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.ERROR,  # ERROR 及以上记录为 breadcrumb
                event_level=logging.ERROR,  # ERROR 及以上作为 event 上报
            ),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
