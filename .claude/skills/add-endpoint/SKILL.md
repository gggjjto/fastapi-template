---
description: Add or change an API endpoint in an existing domain. Use when a new route or modification to an existing route is needed.
disable-model-invocation: true
---

# Add Endpoint

Use this workflow to add or change an API endpoint in an existing domain.

## Inputs

Identify:

- HTTP method and path.
- Request body, query params, and path params.
- Success response shape.
- Expected errors.
- Auth/permission requirement.

## Workflow

1. Locate the owning domain.
2. Follow `.claude/rules/fastapi-endpoint-add.md`.
3. Update schemas first, then repository/service/router as needed.
4. Keep router handlers thin and return `ApiResponse.ok(...)`.
5. Add `responses=` for expected non-200 outcomes.
6. Add or update integration tests with `test-writer`.
7. Run docs maintenance check.
8. Verify with focused tests and quality gates.

## Verification

```bash
uv run pytest tests/<domain>/test_<domain>.py -v
uv run ruff check .
uv run mypy app
```

## Output

Return:

1. Endpoint behavior added or changed.
2. Error cases covered.
3. Tests and checks run.
4. Documentation decision.
