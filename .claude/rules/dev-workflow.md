---
description: Commit and quality gate conventions for this project — applied globally
globs: "**/*"
---

## Quality gates (must all pass before committing)

```bash
uv run ruff check .            # lint
uv run ruff format --check .   # format
uv run mypy app                # type checking
```

Or: `make ci` (lint + format-check + typecheck + cov)

Auto-fix ruff errors first: `uv run ruff check --fix . && uv run ruff format .`

Mypy errors must be fixed properly — not suppressed with `# type: ignore` unless the root cause is a known external library type mismatch. Always note why in the ignore comment.

## Documentation check

Before committing, check whether the change affects setup, APIs, configuration, tests, CI/CD, security posture, or AI workflow. If it does, update the smallest relevant document according to `.claude/rules/docs-maintenance.md`.

## Commit style

Conventional commits. One logical change per commit. Subject under 72 characters.

```
<type>: <imperative description>
```

| Type | When |
|---|---|
| `feat` | New feature or endpoint |
| `fix` | Bug fix or type error |
| `ci` | CI/CD changes |
| `deps` | Dependency updates |
| `docs` | README, CLAUDE.md, comments |
| `chore` | Cleanup, rename, delete unused |
| `refactor` | Restructure without behaviour change |
| `style` | Formatting, whitespace |
| `test` | Adding or updating tests |

## Grouping commits

Group by intent, not by file. Same root cause → one commit. Unrelated changes → separate commits.

## No force pushes to main
