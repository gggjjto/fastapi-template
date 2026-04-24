---
name: dev-workflow
description: Development workflow for this project. Covers the full cycle of making changes, running quality checks, writing commit messages, and pushing — based on the project owner's habits.
---

# Dev Workflow

Follow this skill when the user asks to ship, review, check, or push code, or when finishing a set of changes.

## The cycle

```
make changes → quality gates → fix everything → commit → push
```

Never skip ahead. Quality gates must all pass before committing.

---

## 1. Quality gates

Run in this order. Each must be clean before moving on.

```bash
uv run ruff check .       # lint
uv run ruff format --check .  # format (check only, don't auto-fix silently)
uv run mypy app           # type checking — must pass, no continue-on-error
```

Or all at once:
```bash
make ci   # lint + format-check + typecheck + cov
```

If ruff has auto-fixable errors (`[*]`), apply them and re-check:
```bash
uv run ruff check --fix .
uv run ruff format .
```

Mypy errors must be fixed properly — not suppressed with `# type: ignore` unless the root cause is a known external library type mismatch (e.g. slowapi handler signature). In that case, note why in the ignore comment.

---

## 2. Commit style

Conventional commits, always. One logical change per commit.

```
<type>: <short description in imperative mood>

[optional body explaining WHY, not WHAT]
```

**Types used in this project:**

| Type | When |
|---|---|
| `feat` | New feature or endpoint |
| `fix` | Bug fix or type error |
| `ci` | CI/CD workflow changes |
| `deps` | Dependency updates |
| `docs` | README, CLAUDE.md, comments |
| `chore` | Housekeeping (cleanup, rename, delete unused) |
| `refactor` | Code restructure without behaviour change |

Keep the subject line under 72 characters. Don't describe *what* the diff already shows — explain *why* when it's non-obvious.

---

## 3. What gets committed together

Group by intent, not by file. Changes that fix the same root cause belong in one commit. Unrelated changes (e.g. a CI fix and a typing fix) get separate commits.

Examples from this project:
- CI cleanup (remove docker.yml + simplify matrix + fix UV_VERSION) → one `ci:` commit
- Mypy type errors across 3 files → one `fix:` commit
- Ruff UP037 + Dockerfile LICENSE → one `fix:` commit because they were found in the same review pass

---

## 4. Before pushing, ask: is the code actually correct?

Run a final sanity check:
```bash
uv run ruff check . && uv run mypy app
```

If the project has tests and you changed behaviour (not just CI/tooling), run them too:
```bash
make test-up   # start postgres + redis
make test
make test-down
```

---

## 5. Push

```bash
git push
```

No force pushes to main. If a push is rejected, investigate before acting.

---

## CI mindset

CI should be a hard gate, not decoration:
- `continue-on-error: true` on a quality check means it does nothing — remove it or remove the check
- Every job in CI should have a clear reason to exist; delete jobs that serve no real purpose for the project type
- Keep CI simple: one matrix entry is not a matrix — drop the `strategy` block

---

## Output

When applying this skill, produce:
1. The result of each quality gate (pass or list of errors)
2. Fixes for any errors found, with a one-line explanation of each
3. A commit (or commits) with conventional messages
4. Confirmation of push
