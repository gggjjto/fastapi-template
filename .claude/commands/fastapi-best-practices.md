# FastAPI Best Practices

Apply production-grade FastAPI conventions to the current task — whether scaffolding a new domain, reviewing existing code, or refactoring. Based on `zhanymkanov/fastapi-best-practices` plus community patterns.

## Workflow

1. Inspect the current backend shape before changing anything.
2. Apply conventions incrementally — avoid rewriting unrelated modules.
3. Prefer consistency with existing patterns when they're already strong.

---

## Project structure — domain-oriented

Organize by domain/feature, not by layer. Each domain owns all its artefacts:

```
app/
├── users/
│   ├── router.py        # HTTP handlers only
│   ├── schemas.py       # Pydantic DTOs (inherit CustomModel)
│   ├── models.py        # SQLAlchemy ORM model
│   ├── dependencies.py  # Resource loading, auth guards
│   ├── service.py       # Business logic; raises domain exceptions
│   ├── repository.py    # All DB queries
│   ├── constants.py     # ErrorCode class
│   └── exceptions.py    # Domain exceptions (UserNotFound, UserEmailConflict…)
├── core/
│   ├── config.py        # pydantic-settings (APP_ prefix)
│   ├── schemas.py       # CustomModel base
│   ├── exceptions.py    # DomainError, ConflictError
│   └── logging.py       # structlog
├── db/
│   ├── base.py          # DeclarativeBase + naming_convention
│   └── session.py       # Engine, DBSession, init_db/reset_db
├── router.py            # Composes all domain routers under /api/v1
└── main.py              # create_app(); hides docs outside dev/test
```

Cross-domain imports must be explicit:
```python
from app.auth import constants as auth_constants
from app.notifications import service as notification_service
```

---

## Async / sync rules

- `async def` → non-blocking I/O only. Blocking inside async freezes the event loop.
- `def` (sync) → FastAPI runs it in a threadpool. Use for blocking libraries.
- CPU-heavy work → separate worker process (Celery, Arq, RQ).
- Prefer `async def` for dependencies too — sync deps run in the threadpool unnecessarily.
- Sync SDK inside async route → use `run_in_threadpool`:
  ```python
  from fastapi.concurrency import run_in_threadpool
  await run_in_threadpool(sync_client.make_request, data=payload)
  ```

---

## Pydantic rules

- All schemas inherit from `app.core.schemas.CustomModel` (`from_attributes=True`, `populate_by_name=True`).
- Use validators aggressively: `Field(min_length=…, pattern=…)`, `EmailStr`, `AnyUrl`, `ge/le`, `Enum`.
- `ValueError` in `@field_validator` → auto becomes `ValidationError` with detail for the client.
- `response_model` must be explicit on every endpoint. Document non-200 codes with `responses=`.
- Hide docs outside dev: `if settings.env not in ("development", "test"): app_configs["openapi_url"] = None`

---

## Dependency rules

- Use dependencies for: auth, resource loading, pagination, permission guards.
- Resource-loading deps raise `HTTPException` directly; services raise `DomainError` subclasses.
- FastAPI caches dependency results per request — chain freely, no overhead for reuse:
  ```python
  async def valid_owned_post(
      post: Post = Depends(valid_post_id),
      token: dict = Depends(parse_jwt_data),
  ) -> Post:
      if post.creator_id != token["user_id"]:
          raise UserNotOwner()
      return post
  ```
- Keep path variable names consistent so chained deps wire automatically:
  ```python
  # /profiles/{profile_id} and /creators/{profile_id} both use valid_profile_id
  async def valid_creator_id(profile: Profile = Depends(valid_profile_id)) -> Profile: ...
  ```

---

## Database rules

SQLAlchemy naming convention (already in `app/db/base.py`):
```python
{"ix": "ix_%(column_0_label)s", "uq": "uq_%(table_name)s_%(column_0_name)s",
 "ck": "ck_%(table_name)s_%(constraint_name)s",
 "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
 "pk": "pk_%(table_name)s"}
```

Table naming: `lower_snake_case`, singular, domain-prefixed (`payment_account`), `_at` for datetime, `_date` for date.

Alembic: migrations named `YYYY-MM-DD_slug.py` (set via `file_template` in `alembic.ini`). Must be static and reversible. New models → import in `app/db/session.py` AND `alembic/env.py`.

SQL-first for complex queries — use `func.json_build_object()` for nested JSON rather than Python assembly.

---

## Testing rules

- `httpx.AsyncClient` with `ASGITransport` — always test against the real ASGI app.
- Shared `client` fixture in `tests/conftest.py`.
- `app.dependency_overrides` to swap deps in tests, not monkeypatching.
- `reset_db()` in an `autouse` fixture per test module.

---

## Background tasks vs queues

| `BackgroundTasks` | Celery / Arq / RQ |
|---|---|
| Sub-second, silent failure OK | Multi-second, retry/DLQ needed |
| In-process (email, log) | CPU-heavy or scheduled |

---

## Middleware

Avoid `BaseHTTPMiddleware` — it can block streaming. Use pure ASGI middleware:
```python
class MyMDW:
    def __init__(self, app: ASGIApp) -> None: self.app = app
    async def __call__(self, scope, receive, send):
        async def send_wrapper(message): await send(message)
        await self.app(scope, receive, send_wrapper)
```

---

## Output

Produce one or more of: domain folder structure, refactor plan, concrete code changes, review checklist, or a short explanation of which convention applies and why. Scaffold the smallest useful thing first.
