# Dev Workflow

Run the full development workflow: quality gates → fix → commit → push. Based on the project's conventions and owner's habits.

## Steps

1. Run all quality checks (`ruff check`, `ruff format --check`, `mypy app`).
2. Fix every error found — ruff auto-fixable issues with `--fix`, mypy errors properly (not suppressed unless external library mismatch).
3. If behaviour changed, run the test suite (`make test`).
4. Commit with a conventional commit message (`feat:`, `fix:`, `ci:`, `deps:`, `docs:`, `chore:`, `refactor:`). Group by intent — one root cause, one commit.
5. Push.

Refer to `skills/dev-workflow/SKILL.md` for full conventions.
