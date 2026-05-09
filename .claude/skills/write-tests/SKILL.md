---
description: Write or improve integration tests for existing code. Use when adding tests to untested endpoints, doing a coverage pass, or reviewing test quality.
disable-model-invocation: true
---

# Write Tests

Use this workflow to add or improve integration tests for existing code.

## Inputs

Identify the target before starting:

- Domain or specific endpoint(s) to test.
- Whether this is a new coverage pass or improving existing tests.

## Workflow

1. Read the target router and service to understand all endpoints, inputs, and error paths.
2. Read existing tests in `tests/<domain>/` to avoid duplication.
3. Identify gaps: success path, validation errors (422), not found (404), conflicts (409), auth failures (401/403).
4. Write tests following `.claude/rules/fastapi-test-writer.md`:
   - Integration tests only — real app, real PostgreSQL, real Redis.
   - Assert `code`, `message`, `data` fields on every response.
   - Keep test data local to each test; use shared fixtures only when they improve readability.
   - No mocks of repositories or services.
5. Run the new tests.
6. Fix any failures — if a test fails due to environment, check containers before changing app code.

## Verification

```bash
make test-up   # if containers aren't running
uv run pytest tests/<domain>/test_<domain>.py -v
```

## Output

Return:

1. Tests added and what each covers.
2. Any gaps intentionally skipped and why.
3. Test run result.
