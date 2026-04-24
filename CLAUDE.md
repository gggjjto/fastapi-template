# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv sync --dev
cp .env.example .env

# Development
make dev          # uvicorn with --reload
make lint         # ruff check
make lint-fix     # ruff check --fix (auto-fix)
make format       # ruff format
make typecheck    # mypy app
make test         # pytest (all tests)
make cov          # pytest with coverage report
make ci           # lint + format-check + typecheck + cov (mirrors CI)

# Run a single test
uv run pytest tests/test_users.py::test_get_user_by_id -v

# Database migrations (PostgreSQL workflow)
make migrate                      # alembic upgrade head
make revision m="describe change" # autogenerate migration (files named YYYY-MM-DD_slug.py)

# Background worker (requires Redis)
uv run arq app.worker.WorkerSettings

# Test containers
make test-up      # start PostgreSQL (5433) + Redis (6380) for tests
make test-down    # stop and remove test containers

# Full local stack (API + PostgreSQL + Redis)
docker compose up
```

## Architecture

The app follows a **domain-oriented** structure: each feature domain owns all its artefacts instead of grouping by layer.

```
app/
├── auth/                # JWT auth domain
│   ├── router.py        # POST /auth/token, /auth/refresh, GET /auth/me
│   ├── schemas.py       # LoginRequest, RefreshRequest, TokenResponse
│   ├── security.py      # hash_password, verify_password, create/decode tokens
│   ├── service.py       # AuthService (login, refresh)
│   ├── dependencies.py  # get_current_user, get_current_active_user, CurrentUser
│   ├── constants.py     # ErrorCode
│   └── exceptions.py    # InvalidCredentials, InvalidToken
├── users/               # One directory per domain
│   ├── router.py        # HTTP handlers only — no business logic
│   ├── schemas.py       # Pydantic DTOs (inherit from core/schemas.py CustomModel)
│   ├── models.py        # SQLAlchemy ORM model
│   ├── dependencies.py  # FastAPI dependencies: resource loading, guards
│   ├── service.py       # Business logic; raises domain exceptions
│   ├── repository.py    # All DB queries
│   ├── constants.py     # ErrorCode class
│   └── exceptions.py    # Domain exceptions (UserNotFound, UserEmailConflict…)
├── health/
│   └── router.py
├── core/
│   ├── config.py        # pydantic-settings; all env vars prefixed APP_
│   ├── schemas.py       # CustomModel base (populate_by_name, from_attributes)
│   ├── response.py      # ApiResponse[T] — unified {code, message, data} envelope
│   ├── pagination.py    # PaginationParams dependency + Page[T] generic model
│   ├── exceptions.py    # Base exceptions (DomainError, ConflictError)
│   ├── error_handlers.py# Global HTTP + validation error handlers
│   ├── middleware.py    # RequestIDMiddleware (X-Request-ID header + structlog bind)
│   ├── limiter.py       # slowapi Limiter instance + 429 handler
│   ├── sentry.py        # init_sentry() — no-op when APP_SENTRY_DSN is empty
│   ├── cache.py         # RedisCache helper (get/set/delete/get_or_set)
│   ├── arq.py           # Arq pool lifecycle + ArqPool dependency alias
│   └── logging.py       # structlog configuration
├── db/
│   ├── base.py          # DeclarativeBase with SQLAlchemy naming_convention
│   ├── session.py       # Engine, DBSession type alias, init_db/reset_db
│   └── redis.py         # Redis connection lifecycle + RedisClient dependency alias
├── router.py            # Top-level APIRouter; composes all domain routers under /api/v1
├── main.py              # create_app() factory; lifespan; middleware stack
└── worker.py            # Arq WorkerSettings + task definitions
```

### Key conventions

- **Response envelope**: All endpoints return `ApiResponse[T]` — `{"code": 200, "message": "success", "data": {...}}`. Errors: `{"code": 4xx, "message": "...", "data": null}`. Use `ApiResponse.ok(data)` in routers.
- **Domain imports**: When a domain needs another domain's code, import explicitly — `from app.auth import constants as auth_constants`.
- **Settings**: All env vars use `APP_` prefix. Access via `get_settings()` (LRU-cached singleton).
- **DB session**: Use `DBSession` type alias from `app.db.session`. Injected per-request via `get_db_session()`.
- **Redis client**: Use `RedisClient` type alias from `app.db.redis`. Only available when `APP_REDIS_URL` is set.
- **Task queue**: Use `ArqPool` type alias from `app.core.arq` to enqueue jobs. Enqueue: `await queue.enqueue_job("task_name", arg)`.
- **Rate limiting**: Apply `@limiter.limit("N/period")` from `app.core.limiter`. The endpoint must have `request: Request` as its first parameter.
- **Auth guard**: Use `CurrentUser = Annotated[User, Depends(get_current_active_user)]` from `app.auth.dependencies`.
- **Domain exceptions**: Services raise `DomainError` subclasses; dependencies raise `HTTPException` directly; routers catch domain exceptions and convert to HTTP responses.
- **Models must be imported** before `Base.metadata` is used. Add new models in both `app/db/session.py` and `alembic/env.py`.
- **Default DB**: SQLite (`sqlite+aiosqlite:///./app.db`) for local dev. Switch to PostgreSQL by changing `APP_DATABASE_URL` and setting `APP_DB_CREATE_TABLES_ON_STARTUP=false`, then use Alembic.
- **Docs visibility**: OpenAPI is hidden (`openapi_url=None`) in any env other than `development` or `test`.
- **CustomModel**: All Pydantic schemas inherit from `app.core.schemas.CustomModel` (`populate_by_name=True`, `from_attributes=True`).

### Optional services

Both Redis and Sentry are opt-in via env vars. The app starts and runs normally without them.

| Feature | Enable via | What it unlocks |
|---|---|---|
| Redis | `APP_REDIS_URL=redis://...` | `RedisClient`, `RedisCache`, `ArqPool` |
| Task queue | `APP_REDIS_URL=redis://...` | `ArqPool` dependency, run `uv run arq app.worker.WorkerSettings` |
| Sentry | `APP_SENTRY_DSN=https://...` | Error tracking; ERROR-level structlog events auto-reported |

### Testing

Tests are **integration tests** and depend on real PostgreSQL + Redis. Start deps with `make test-up` (uses `docker-compose.test.yml`, ports 5433/6380, tmpfs storage).

- `httpx.AsyncClient` + `ASGITransport` drives the real app; `asgi-lifespan.LifespanManager` triggers startup/shutdown so `RedisClient` and `ArqPool` are really initialised.
- `conftest.py` sets `APP_ENV=test`, `APP_DATABASE_URL` (PG), `APP_REDIS_URL` via `os.environ.setdefault` before importing the app.
- An autouse fixture `_reset_state` runs before every test: `reset_db()` (drop_all + create_all) and `FLUSHDB`.
- Session-scoped event loop via `asyncio_default_fixture_loop_scope = "session"` — required because module-level `engine` / Redis pools bind to the first loop.
- Use `app.dependency_overrides` to swap dependencies rather than monkeypatching internals.
- Only `app/core/sentry.py` is excluded from coverage (needs live DSN).

## Skill

A `/fastapi-best-practices` skill lives in `skills/fastapi-best-practices/SKILL.md` and `.claude/commands/fastapi-best-practices.md`. Use it when scaffolding new domains, reviewing architecture decisions, choosing between `async def` and `def`, designing dependencies, or adding new endpoints.
