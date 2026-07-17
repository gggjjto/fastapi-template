# Backend Template Convention

This repository's current core is a FastAPI backend template. Keep it strong as
the default path even as the repository grows into a broader rapid-development
workspace.

## Required Core

- `apps/api/app/core`: configuration, response envelope, error handling, i18n, logging,
  request context, rate limiting, Redis helpers, Arq lifecycle, and Sentry setup.
- `apps/api/app/db`: SQLAlchemy base, async engine/session lifecycle, and Redis client
  lifecycle.
- `apps/api/app/health`: public health endpoint for smoke checks and deployments.
- `apps/api/tests`: integration-style tests that exercise the real app with PostgreSQL
  and Redis test services.
- `apps/api/Makefile`: the backend command contract for local development and CI.
- `apps/api/pyproject.toml`: Python package metadata, runtime dependencies, dev tools,
  Ruff, pytest, coverage, and mypy configuration.

## Optional Example Domains

- `apps/api/app/users`: example resource domain and a useful starting point for CRUD
  patterns.
- `apps/api/app/auth`: JWT sessions and RBAC. Keep it for SaaS/API products, but make it
  optional for public prototypes or one-off internal tools.
- `apps/api/app/worker.py`: Arq worker settings and scheduled task registration. Keep it
  when a project needs background jobs.

## Template Rules

- Keep routers thin; business logic belongs in services, database access in
  repositories.
- New domains should mirror the existing domain-oriented structure:
  `router.py`, `schemas.py`, `models.py`, `repository.py`, `service.py`,
  `dependencies.py`, `constants.py`, and `exceptions.py` as needed.
- Keep optional infrastructure controlled by environment variables so generated
  projects can start small.
- Use `scripts/doctor.py` or `make doctor` to check local prerequisites before first setup.
- Use `scripts/create_project.py` as the first generator path until the template
  catalog exists.

## Quality Gate

Backend changes should pass from `apps/api`:

```bash
make lint
make format-check
make typecheck
make check-ai
make test
```

From the repository root, use the `api-*` proxy targets:

```bash
make api-test-up
make api-ci
make api-test-down
```
