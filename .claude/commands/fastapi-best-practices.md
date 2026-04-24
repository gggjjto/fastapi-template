# FastAPI Best Practices

Apply production-grade FastAPI conventions to the current task — whether scaffolding a new domain, reviewing existing code, or refactoring. Based on `zhanymkanov/fastapi-best-practices` plus community patterns.

## Workflow

1. Inspect the current backend shape before changing anything.
2. Apply conventions incrementally — avoid rewriting unrelated modules.
3. Prefer consistency with the existing codebase when strong patterns already exist.

---

## Project structure — domain-oriented

Organize code by domain/feature, not by layer. Each domain owns all of its artefacts.

```
app/
├── users/
│   ├── router.py        # HTTP handlers only
│   ├── schemas.py       # Pydantic DTOs (inherit CustomModel)
│   ├── models.py        # SQLAlchemy ORM model
│   ├── dependencies.py  # FastAPI dependencies (resource loading, auth guards)
│   ├── service.py       # Business logic; raises domain exceptions
│   ├── repository.py    # All DB queries
│   ├── constants.py     # ErrorCode class, module-level literals
│   └── exceptions.py    # Domain exceptions (UserNotFound, UserEmailConflict…)
├── health/
│   └── router.py
├── core/
│   ├── config.py        # Global pydantic-settings (APP_ prefix)
│   ├── schemas.py       # CustomModel base (populate_by_name, from_attributes)
│   ├── exceptions.py    # Base exceptions (DomainError, ConflictError…)
│   └── logging.py       # structlog configuration
├── db/
│   ├── base.py          # DeclarativeBase with naming_convention
│   └── session.py       # Engine, DBSession type alias, init_db/reset_db
├── router.py            # Top-level APIRouter; mounts all domain routers under /api/v1
└── main.py              # create_app() factory; lifespan; hides docs in prod
```

When a domain needs something from another domain, import explicitly:
```python
from app.auth import constants as auth_constants
from app.notifications import service as notification_service
```

---

## Async / sync route rules

- `async def` — only for non-blocking I/O that uses `await`. FastAPI trusts you; blocking inside async freezes the event loop.
- `def` (sync) — FastAPI runs it in a threadpool automatically. Use for blocking libraries with no async API.
- CPU-heavy work belongs in a separate worker process (Celery, Arq, RQ), not in a threadpool.
- Same logic applies to **dependencies**: prefer `async def`; sync deps run in the threadpool unnecessarily.
- For synchronous SDKs inside async routes, use `run_in_threadpool`:
  ```python
  from fastapi.concurrency import run_in_threadpool
  await run_in_threadpool(sync_client.make_request, data=payload)
  ```

---

## Pydantic schema rules

- Use a global `CustomModel` base (`app/core/schemas.py`) so all schemas inherit consistent config (`populate_by_name=True`, `from_attributes=True`).
- Leverage built-in validators aggressively: `Field(min_length=…, pattern=…)`, `EmailStr`, `AnyUrl`, `ge`/`le`, `Enum`.
- `ValueError` raised inside `@field_validator` automatically becomes a `ValidationError` — use it for field-level business rules.
- Keep `response_model` explicit on every endpoint; document non-200 status codes with the `responses` parameter.
- Every `Field` must include `description` and `examples`. Input schemas also add validation constraints (`min_length`, `max_length`, `ge`, `le`). Output schemas skip constraints.
- Hide OpenAPI docs in non-dev environments:
  ```python
  if settings.env not in ("development", "test"):
      app_configs["openapi_url"] = None
  ```

---

## Dependency rules

- Use dependencies for **cross-cutting request concerns**: auth, resource loading (valid_user_id), pagination, permission guards.
- Resource-loading dependencies raise `HTTPException` directly; domain services raise `DomainError` subclasses.
- **Dependency caching**: FastAPI caches the result per-request. Split dependencies into small, focused functions and chain them freely — there is no call overhead for re-use.
- **Chain dependencies** to avoid duplicated validation logic:
  ```python
  async def valid_owned_post(
      post: Post = Depends(valid_post_id),
      token: dict = Depends(parse_jwt_data),
  ) -> Post:
      if post.creator_id != token["user_id"]:
          raise UserNotOwner()
      return post
  ```
- **REST path variable consistency**: reuse the same path variable name across chained dependencies so FastAPI wires them automatically:
  ```python
  # Both /profiles/{profile_id} and /creators/{profile_id} can share valid_profile_id
  async def valid_creator_id(profile: Profile = Depends(valid_profile_id)) -> Profile: ...
  ```

---

## Database and migration rules

### SQLAlchemy naming convention (already set in `app/db/base.py`)
```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

### Table naming rules
- `lower_snake_case`, singular (`post`, `user_playlist`)
- Group related tables with a domain prefix (`payment_account`, `payment_bill`)
- `_at` suffix for `DateTime` columns, `_date` for `Date` columns
- Use abstract names in join tables (`post_id`), concrete names in domain context (`course_id`)

### Alembic rules
- Migration files use date-slug naming: `2024-08-01_add_users_table.py` (set in `alembic.ini` via `file_template`)
- Migrations must be static and reversible; review autogenerated output before committing
- New ORM models must be imported in `app/db/session.py` and `alembic/env.py` for metadata registration

### SQL-first for complex queries
Prefer SQL / SQLAlchemy Core for joins, aggregations, and nested JSON responses rather than Python-side assembly:
```python
func.json_build_object(
    text("'id', profiles.id"),
    text("'username', profiles.username"),
).label("creator")
```

---

## Testing rules

- Use `httpx.AsyncClient` with `ASGITransport` from day one — always test against the real ASGI app.
- Share the `client` fixture in `tests/conftest.py`:
  ```python
  @pytest.fixture
  async def client() -> AsyncGenerator[AsyncClient, None]:
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
          yield ac
  ```
- Use `app.dependency_overrides` to swap auth/session dependencies in tests rather than monkeypatching internals.
- Integration tests depend on real PostgreSQL + Redis. Start deps with `make test-up` (ports 5433/6380). Call `reset_db()` + `FLUSHDB` in an `autouse` fixture before every test.

---

## Background tasks vs task queues

| Use `BackgroundTasks` | Use Celery / Arq / RQ |
|---|---|
| Sub-second work | Multi-second tasks |
| Silent failure acceptable | Retry / dead-letter needed |
| In-process (send email, log event) | CPU-heavy or scheduled work |

---

## Middleware

Avoid `BaseHTTPMiddleware` in production — it can serialize streaming responses. Implement pure ASGI middleware instead:
```python
class LogResponseMDW:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_wrapper(message: Message):
            await send(message)
        await self.app(scope, receive, send_wrapper)
```

---

## Router and handler rules

- Every route decorator must include `summary`, `description`, and `response_model`.
- Keep docstrings out of handler functions — put the text in the decorator instead.
- All endpoints return `ApiResponse[T]` — `{"code": 200, "message": "success", "data": {...}}`. Use `ApiResponse.ok(data)` in routers.
- Errors return `{"code": 4xx, "message": "...", "data": null}`.

---

## Output

When applying this skill, produce one or more of the following:
- A proposed domain folder structure
- A refactor plan with specific file moves
- Concrete code changes
- A review checklist
- A short explanation of which convention is being applied and why

Scaffold the smallest useful structure first; avoid adding infrastructure the project does not need yet.
