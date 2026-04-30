# Ship Change

Use this workflow to finish a set of changes before commit, PR, or handoff.

## Workflow

1. Review the diff and group changes by intent.
2. Run `docs-maintainer` for documentation impact.
3. Run `security-reviewer` when the change touches auth, user data, config, CI, or public API behavior.
4. Run or request `test-writer` review when behavior changed.
5. Run quality gates.
6. Summarize what changed, what was verified, and any remaining risk.

## Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

When behavior changed and test dependencies are available:

```bash
make test-up
make test
make test-down
```

If test dependencies are unavailable, report exactly what could not run and why.

## Commit guidance

Use conventional commits and group by intent:

```text
feat: add order creation endpoint
fix: handle expired refresh tokens
docs: document CI security scans
```

Do not commit or push unless the user explicitly asks.

## Output

Return:

1. Change summary.
2. Documentation/security/test review result.
3. Quality gate results.
4. Suggested commit message if useful.
