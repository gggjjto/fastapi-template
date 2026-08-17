# AGENTS.md

Repository map and completion contract for coding agents. Detailed workflows and
rules live under [`.agents/`](.agents/README.md); keep this file concise.

## Start here

```bash
pnpm install
cd apps/api && uv sync --dev && cp .env.example .env
```

Use `make doctor` to check local prerequisites. PostgreSQL and Redis are required
for API integration tests; start them with `make api-test-up`.

## Commands

```bash
# Whole workspace
make dev
make lint
make typecheck
make test
make build

# Backend
make api-dev
make api-worker
make api-crawler-dispatcher
make api-crawler-scheduler
make api-lint
make api-format-check
make api-typecheck
make api-test
make api-ci
make api-check-ai

# Frontends
make admin-dev
make admin-lint
make admin-typecheck
make admin-build
make web-dev
make web-lint
make web-typecheck
make web-build

# Test services and migrations
make api-test-up
make api-test-down
make api-migrate
make api-revision m="describe change"
```

Run one API test from `apps/api` with
`uv run pytest tests/path/test_file.py::test_name -v`.

## Architecture map

- [`docs/README.md`](docs/README.md) — documentation authority, lifecycle,
  catalog, and conflict-resolution rules. Read this before treating prose as
  implementation context.
- `apps/api/app/` — domain-oriented FastAPI application. Routers handle HTTP,
  services own business logic, and repositories own persistence.
- `apps/api/tests/` — integration tests using the real app, PostgreSQL, and Redis.
- `apps/admin/` — Next.js management console and browser BFF.
- `apps/web/` — minimal Next.js business frontend.
- [`docs/architecture.md`](docs/architecture.md) — repository and runtime boundaries.
- [`docs/backend.md`](docs/backend.md) — API, data, authentication, and crawler contracts.
- [`docs/harness-engineering.md`](docs/harness-engineering.md) — agent Harness
  architecture, ownership, quality status, and promotion triggers.

## Workflow routing

`.agents/` is the repository-local source of truth:

- [`.agents/README.md`](.agents/README.md) indexes skills and workflow ownership.
- [`.agents/rules/INDEX.md`](.agents/rules/INDEX.md) indexes reusable rules.
- [`.agents/requirements.md`](.agents/requirements.md) contains active requirements
  only; Git history and durable design documents archive completed work.
- [`.agents/requirements/INDEX.md`](.agents/requirements/INDEX.md) indexes deeper
  requirement notes.
- `.agents/skills/<name>/SKILL.md` contains on-demand workflows. Load the relevant
  skill before following it.

Use the smallest workflow that fits the task. Prefer existing patterns and
dependencies; avoid speculative layers. Install community skills only through the
process documented in `.agents/README.md` so `skills-lock.json` stays authoritative.

## Invariants

- Python requires 3.12 or newer and modules use future annotations.
- API DTOs inherit from `CustomModel`; list endpoints use `Page[T]`.
- Inject `DBSession` and `RedisClient` through existing aliases.
- Register every Hatchet task in `create_worker()` and keep the API independent of Hatchet credentials.
- Add crawler business logic only under `app/crawler/handlers`; the runner owns persistence, retries, and network policy.
- Keep optional Redis and Sentry behavior environment-controlled.
- Preserve middleware order intentionally; FastAPI middleware registration is LIFO.
- Never add tool-specific AI workflow directories or copy `.omx` runtime state.
- Update documentation when setup, APIs, configuration, tests, CI, security, or the
  Harness contract changes.

## Completion contract

Before reporting completion, run the smallest targeted test that proves the change,
then the affected lint/type/build gates. Harness changes must pass
`make harness-check`. If full integration tests cannot run,
state the missing service and report the next-best checks; never claim an unrun gate.

## Code Review Rules

### Tenant and authentication boundaries

- Flag tenant-owned reads or writes that are not constrained by `tenant_id`, or
  authorization paths that can expose whether a cross-tenant resource exists.
  Safe path: enforce tenant scope in the repository query and return `404` across
  tenant boundaries.

### Crawler safety and lifecycle

- Flag changes that weaken SSRF, redirect, timeout, or response-size protections,
  or let dispatchers and late runners overwrite terminal job states. Safe path:
  keep network policy in the shared HTTP client and terminal transitions atomic.

### Data migrations

- Flag model changes without a deployable Alembic upgrade and downgrade, including
  enum or check-constraint drift and missing data migration for renamed roles.
