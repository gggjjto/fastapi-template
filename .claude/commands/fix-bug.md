# Fix Bug

Use this workflow for bug fixes and regressions.

## Workflow

1. Reproduce or explain the observed failure.
2. Locate the smallest affected area.
3. Add a failing test when the bug changes runtime behavior.
4. Fix the root cause with the smallest code change.
5. Run the failing test again.
6. Run related tests and quality gates.
7. Run docs maintenance check if behavior, config, API, or workflow changed.

## Guardrails

- Do not guess at broad rewrites.
- Do not weaken validation or error handling to make tests pass.
- Do not suppress mypy errors without a specific external typing reason.
- If the failure is environmental, report the missing dependency instead of changing app code.

## Verification

```bash
uv run pytest <path-or-nodeid> -v
uv run ruff check .
uv run mypy app
```

## Output

Return:

1. Root cause.
2. Fix summary.
3. Regression test added or why not.
4. Commands run and results.
