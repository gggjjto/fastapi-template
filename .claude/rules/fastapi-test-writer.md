---
description: Rules for writing tests in this FastAPI template
paths:
  - "tests/**/*.py"
  - "app/**/*.py"
---

## Test style

Tests are integration-first. Use the real FastAPI app, real PostgreSQL, and real Redis through existing fixtures.

Do:

- Put tests under `tests/<domain>/test_<domain>.py`.
- Reuse shared fixtures from `tests/conftest.py`.
- Cover success, validation errors, not found, conflicts, and auth failures when relevant.
- Assert the unified response envelope: `code`, `message`, `data`.
- Keep test data explicit and local to the test unless a fixture improves readability.

Avoid:

- Mocking repositories or services for normal API behavior.
- Monkeypatching internals when `app.dependency_overrides` can express the dependency swap.
- Depending on test execution order.

## Running tests

Integration tests require containers:

```bash
make test-up
make test
make test-down
```

For focused iteration:

```bash
uv run pytest tests/<domain>/test_<domain>.py -v
```

If tests fail with connection errors to PostgreSQL or Redis, first verify `make test-up` is running before changing application code.
