---
description: Rules for scaffolding new FastAPI domains in this project
globs: app/**/*.py, tests/**/*.py
---

## New domain scaffold

Create the smallest domain that can support the requested behavior.

Recommended files:

```text
app/<domain>/
├── __init__.py
├── constants.py
├── exceptions.py
├── models.py
├── repository.py
├── schemas.py
├── service.py
└── router.py
tests/<domain>/
└── test_<domain>.py
```

Add `dependencies.py` only when the domain needs resource-loading, ownership, permission, or reusable guard dependencies.

Add `utils.py` only for pure, non-business helper functions that would otherwise make `service.py` noisy. Do not put database queries or HTTP concerns there.

## Registration checklist

- Include the router from `app/router.py`.
- Import new ORM models in `app/db/session.py`.
- Import new ORM models in `alembic/env.py`.
- Add an Alembic migration when persistent schema changes.
- Mirror route metadata style: `summary`, `description`, `response_model`.

## Layer responsibilities

- `router.py`: HTTP adaptation only, returns `ApiResponse.ok(...)`.
- `service.py`: business rules, raises domain exceptions.
- `repository.py`: SQLAlchemy queries only.
- `schemas.py`: request/response DTOs using `CustomModel`.
- `exceptions.py`: domain-specific `DomainError` subclasses.
- `constants.py`: error codes and stable literals.
