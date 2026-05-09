---
description: Commit and quality gate conventions for this project — applied globally
---

## How checks are enforced (best-effort vs hard guarantees)

Nothing can **mathematically force** an AI to run commands; reliability comes from **layers**:


| Layer                                         | What runs                                | Role                                                     |
| --------------------------------------------- | ---------------------------------------- | -------------------------------------------------------- |
| **AI instructions** (this file + `CLAUDE.md`) | Agent should run gates after edits       | Catches issues before you commit                         |
| **pre-commit** (`.pre-commit-config.yaml`)    | `ruff` + `mypy` on `git commit`          | Blocks bad commits locally if hooks are installed        |
| **CI** (`.github/workflows/ci.yml`)           | Lint, format, mypy, tests, migrations, … | Authoritative on push/PR; required on protected branches |


**Install once per clone:** `uv run pre-commit install` — then every commit runs the hooks unless bypassed.

**Bypass:** `git commit --no-verify` skips hooks — rely on CI and review for branches that matter.

**Tests:** Integration tests need PostgreSQL + Redis; they are **not** in pre-commit (too heavy). Use `make test` / `make ci` locally before push, or rely on CI.

## After AI or manual code changes

Before treating work as done or committing:

1. Run `**make ci`** when behaviour or types might change (lint + format + mypy + coverage tests), or at minimum `**make lint`**, `**make format-check**`, `**make typecheck**`.
2. After fixing Ruff issues: `make lint-fix` / `make format` as needed.

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


| Type       | When                                 |
| ---------- | ------------------------------------ |
| `feat`     | New feature or endpoint              |
| `fix`      | Bug fix or type error                |
| `ci`       | CI/CD changes                        |
| `deps`     | Dependency updates                   |
| `docs`     | README, CLAUDE.md, comments          |
| `chore`    | Cleanup, rename, delete unused       |
| `refactor` | Restructure without behaviour change |
| `style`    | Formatting, whitespace               |
| `test`     | Adding or updating tests             |


## Grouping commits

Group by intent, not by file. Same root cause → one commit. Unrelated changes → separate commits.

## No force pushes to main

