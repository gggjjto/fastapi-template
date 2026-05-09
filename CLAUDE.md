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
uv run pytest tests/users/test_users.py::test_get_user_by_id -v

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

- **Python version**: Requires Python ≥3.12. The codebase uses PEP 695 generic class syntax (`class ApiResponse[T]`, `class Page[T]`).
- **Future annotations**: Every module starts with `from __future__ import annotations` to defer annotation evaluation.
- **Pagination**: List endpoints inject `Pagination` (a `PaginationParams` dependency alias from `app.core.pagination`) and return `Page[T]` as the `data` field. `Page` carries `items`, `total`, `limit`, and `offset`.
- **DB session**: Use `DBSession` type alias from `app.db.session`. Injected per-request via `get_db_session()`.
- **Redis client**: Use `RedisClient` type alias from `app.db.redis`. Only available when `APP_REDIS_URL` is set.
- **Task queue**: Use `ArqPool` type alias from `app.core.arq` to enqueue jobs. Enqueue: `await queue.enqueue_job("task_name", arg)`. New task functions must also be registered in `WorkerSettings.functions` in `app/worker.py`.
- **Middleware order**: `add_middleware()` calls are LIFO — the last-added middleware wraps outermost (first to handle requests). Current order: GZip (outermost) → RequestID → CORS (innermost).

### Optional services

Both Redis and Sentry are opt-in via env vars. The app starts and runs normally without them.


| Feature    | Enable via                   | What it unlocks                                                  |
| ---------- | ---------------------------- | ---------------------------------------------------------------- |
| Redis      | `APP_REDIS_URL=redis://...`  | `RedisClient`, `RedisCache`, `ArqPool`                           |
| Task queue | `APP_REDIS_URL=redis://...`  | `ArqPool` dependency, run `uv run arq app.worker.WorkerSettings` |
| Sentry     | `APP_SENTRY_DSN=https://...` | Error tracking; ERROR-level structlog events auto-reported       |


> **Note**: `redis` is pinned to `<6` because `arq <=0.28` does not support redis 6/7. Do not bump this until arq releases support.

### Testing

Tests are **integration tests** and depend on real PostgreSQL + Redis. Start deps with `make test-up` (uses `docker-compose.test.yml`, ports 5433/6380, tmpfs storage).

- `httpx.AsyncClient` + `ASGITransport` drives the real app; `asgi-lifespan.LifespanManager` triggers startup/shutdown so `RedisClient` and `ArqPool` are really initialised.
- `conftest.py` sets `APP_ENV=test`, `APP_DATABASE_URL` (PG), `APP_REDIS_URL` via `os.environ.setdefault` before importing the app.
- An autouse fixture `_reset_state` runs before every test: `reset_db()` (drop_all + create_all) and `FLUSHDB`.
- Session-scoped event loop via `asyncio_default_fixture_loop_scope = "session"` — required because module-level `engine` / Redis pools bind to the first loop.
- Use `app.dependency_overrides` to swap dependencies rather than monkeypatching internals.
- Only `app/core/sentry.py` is excluded from coverage (needs live DSN).

Test files mirror the domain structure under `tests/`:

```
tests/
├── conftest.py
├── auth/
│   └── test_auth.py
├── core/
│   ├── test_cache.py
│   ├── test_middleware.py
│   └── test_tasks.py
├── health/
│   └── test_health.py
└── users/
    └── test_users.py
```

## Commands and Skills

Development workflows are available as skills in `.claude/skills/`:

- `/feature` — complete development workflow: confirm requirements → write code → write tests → quality gates → commit.
- `/refactor` — safe refactoring: establish test baseline → make surgical changes → verify behavior unchanged → commit.
- `/fastapi-best-practices` — apply conventions when scaffolding domains, reviewing architecture, or adding endpoints.
- `/dev-workflow` — run quality gates (ruff + mypy), fix errors, write conventional commits, and push.
- `/add-domain` — scaffold a new domain with router/service/repository/schema/model/test flow.
- `/add-endpoint` — add or change an endpoint in an existing domain.
- `/fix-bug` — reproduce, add a failing test when appropriate, fix, and verify.
- `/db-change` — update ORM models, migrations, repository/service/tests, and docs.
- `/security-review` — review auth, authorization, JWT, CORS, rate limiting, OpenAPI exposure, secrets, validation, and CI gates.
- `/ship-change` — run documentation/security/test review and quality gates before handoff or commit.
- `/karpathy-guidelines` — apply before writing new code: surface assumptions, keep changes surgical, avoid speculative features.
- `/gather-reqs` — gather and record feature requirements before coding: structured questions → confirmed spec → saved to requirements log.
- `/discuss-reqs` — collaborative requirements analysis: proactively surface blind spots, edge cases, and missing details through iterative discussion before coding.
- `/breakdown` — decompose a large feature into ordered, reviewable PRs with explicit layer dependencies.
- `/write-tests` — write or improve integration tests for existing code: gap analysis → tests → run.
- `/write-pr` — generate a filled PR description from the current branch diff and commit history.
- `/upgrade-deps` — safely upgrade a dependency: changelog analysis → version bump → test validation.

Documentation maintenance rules live in `.claude/rules/docs-maintenance.md`. Apply them before finishing any change that affects setup, APIs, configuration, tests, CI/CD, security posture, or AI workflow.