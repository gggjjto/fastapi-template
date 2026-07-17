# Remaining Template Execution Plan

This plan covers the remaining work after the repository has been reshaped into
a monorepo skeleton with the FastAPI backend under `apps/api`.

## Current Starting Point

Implemented but not yet committed:

- Phase 1 template hardening:
  `scripts/doctor.py`, `scripts/create_project.py`, `docs/conventions/`, and
  `docs/recipes/`.
- Phase 2 monorepo skeleton:
  backend moved to `apps/api`, root `Makefile` delegates to `api-*` targets,
  CI/Dependabot/pre-commit/docs updated for the new path.

Known verification already completed:

- `make api-ci`: 95 tests passed, coverage 91%.
- `make api-docker-build`: passed.
- Alembic `upgrade head` and `downgrade base`: passed on a clean test database.

## Progress Log

- Commit 1 and Commit 2 were completed as `refactor: move api into apps workspace`.
- Commit 3 was completed as `docs: add remaining template execution roadmap`.
- Phase 3 was completed with manifest, template-aware generator, and generated
  FastAPI smoke-test commits.
- Phase 4 has started with a real Next.js web app plus pnpm/Turborepo
  workspace orchestration.
- Phase 4.3 added `packages/config` for shared TypeScript and ESLint defaults,
  and `apps/web` imports it through a workspace dependency.

## Commit Strategy

Use small commits with one reviewable purpose each. Do not mix generator logic,
frontend/Turborepo setup, and backend migration fixes in the same commit.

### Commit 1: `chore: add rapid template tooling`

Include:

- `scripts/doctor.py`
- `scripts/create_project.py`
- `docs/conventions/backend-template.md`
- `docs/recipes/*`
- `tests/core/test_template_scripts.py`
- README/Makefile entries for template tooling if not already captured by the
  monorepo commit

Verify before commit:

```bash
make api-lint
make api-format-check
make api-typecheck
make api-check-ai
```

### Commit 2: `refactor: move api into apps workspace`

Include:

- Moves from root `app/`, `tests/`, `alembic/`, `locales/`, Docker files,
  `pyproject.toml`, and `uv.lock` into `apps/api/`.
- Root `Makefile` delegation to `api-*` commands.
- `apps/api/Makefile`.
- CI, Dependabot, pre-commit, AGENTS, README, and command path updates.
- `scripts/check_ai_workflow.py` path robustness fix.

Verify before commit:

```bash
make api-test-up
make api-ci
make api-test-down
make api-docker-build
```

For Alembic, verify against a clean test DB:

```bash
make api-test-down
make api-test-up
cd apps/api
APP_ENV=test \
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/app_test \
APP_DB_CREATE_TABLES_ON_STARTUP=false \
APP_JWT_SECRET=local-migration-secret-0123456789abcdef \
uv run alembic upgrade head
APP_ENV=test \
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/app_test \
APP_DB_CREATE_TABLES_ON_STARTUP=false \
APP_JWT_SECRET=local-migration-secret-0123456789abcdef \
uv run alembic downgrade base
cd ../..
make api-test-down
```

### Commit 3: `docs: add remaining template execution roadmap`

Include:

- This file.

Verify before commit:

```bash
make api-check-ai
```

## Phase 3: Template Catalog

Goal: make project generation template-aware instead of only copying the whole
workspace.

### Batch 3.1: Template Manifest Schema

Commit: `feat: add template manifest schema`

Tasks:

- Add `templates/README.md`.
- Add `templates/fastapi-api/template.json`.
- Document manifest fields:
  `id`, `name`, `description`, `source`, `default_target`, `required_tools`,
  `generated_paths`, `post_create_steps`, and `verification`.
- Add tests for manifest loading and validation.

Acceptance criteria:

- Invalid manifests fail with a clear error.
- `templates/fastapi-api/template.json` points to the maintained `apps/api`
  source.
- Tests cover required fields and unknown template IDs.

Verification:

```bash
make api-lint
make api-format-check
cd apps/api && uv run pytest tests/core/test_template_scripts.py -v
```

### Batch 3.2: Template-Aware Generator

Commit: `feat: support template selection in project generator`

Tasks:

- Extend `scripts/create_project.py` with `--template fastapi-api`.
- Keep the default template as `fastapi-api`.
- Copy only declared paths from the selected template.
- Update generated next-step instructions based on the template manifest.
- Add `make create-project name=... target=... template=fastapi-api` support.

Acceptance criteria:

- `python3 scripts/create_project.py my-api /tmp/my-api --template fastapi-api`
  creates a project with `apps/api`.
- The generated project excludes `.git`, `.venv`, caches, coverage, and local
  env files.
- README and Docker image names are rewritten for the new project.

Verification:

```bash
make api-lint
make api-format-check
cd apps/api && uv run pytest tests/core/test_template_scripts.py -v
```

### Batch 3.3: Template Smoke Test

Commit: `test: smoke test generated fastapi template`

Tasks:

- Add a test that creates a temporary project from `fastapi-api`.
- In the generated project, run lightweight checks that do not require Docker:
  `make api-lint`, `make api-format-check`, and `make api-typecheck`.
- Document how to run the heavier generated-project CI manually.

Acceptance criteria:

- Generated project can run static checks from its own root.
- Smoke test is deterministic and does not write outside a temporary directory.

Verification:

```bash
make api-ci
```

## Phase 4: Optional Frontend and Turborepo

Trigger: start only when adding a real `apps/web` or JS/TS shared package.

### Batch 4.1: Frontend App Skeleton

Commit: `feat: add web app workspace`

Tasks:

- Add `apps/web` with the chosen frontend stack.
- Add frontend README, lint, typecheck, test, and build commands.
- Keep API and web runnable independently.

Acceptance criteria:

- `cd apps/web && pnpm lint` passes.
- `cd apps/web && pnpm typecheck` passes.
- Root docs explain how API and web run together.

Verification:

```bash
make api-ci
cd apps/web && pnpm lint && pnpm typecheck
```

### Batch 4.2: Turborepo Workspace

Commit: `chore: add turborepo workspace orchestration`

Tasks:

- Add root `package.json`, `pnpm-workspace.yaml`, and `turbo.json`.
- Add root scripts:
  `dev`, `lint`, `typecheck`, `test`, `build`, and `clean`.
- Configure Turbo to call API Make targets through package scripts rather than
  replacing `uv` or backend Make commands.

Acceptance criteria:

- `pnpm lint`, `pnpm typecheck`, and `pnpm test` coordinate all available
  workspace projects.
- `make api-ci` still works independently.
- Turbo cache does not hide Python command failures.

Verification:

```bash
pnpm install
pnpm lint
pnpm typecheck
pnpm test
make api-ci
```

### Batch 4.3: Shared Packages

Commit: `feat: add shared workspace packages`

Tasks:

- Add `packages/config` for shared JS/TS config.
- Add `packages/sdk` if API client generation is needed.
- Add `packages/ui` only when there is a real shared UI need.

Acceptance criteria:

- Packages are imported by at least one app.
- Unused placeholder packages are avoided.
- Workspace build order is handled by Turbo dependencies.

Verification:

```bash
pnpm build
pnpm test
make api-ci
```

## Phase 5: Productized Developer Experience

Goal: make the repository feel like a personal project launcher.

### Batch 5.1: Template Options

Commit: `feat: add selectable template options`

Tasks:

- Add generator flags for optional capabilities:
  `--with-auth`, `--with-rbac`, `--with-worker`, `--with-redis`,
  `--with-sentry`, and `--with-ai`.
- Start with documentation and manifest support before deleting files from
  generated projects.
- Add tests for supported and unsupported option combinations.

Acceptance criteria:

- Unsupported combinations fail clearly.
- Default generation remains stable.
- Option docs say exactly what files and env vars are affected.

Verification:

```bash
make api-ci
```

### Batch 5.2: Doctor Profiles

Commit: `feat: add doctor profiles`

Tasks:

- Add `scripts/doctor.py --template fastapi-api`.
- Later add `--template fullstack` after frontend exists.
- Check only tools required by the selected template.

Acceptance criteria:

- Backend-only projects are not warned about missing Node tools.
- Fullstack projects are warned about missing Node/pnpm only after that template
  exists.

Verification:

```bash
make doctor
python3 scripts/doctor.py --template fastapi-api
make api-ci
```

### Batch 5.3: Recipes and Versioning

Commit: `docs: productize template recipes and versioning`

Tasks:

- Add recipes for Stripe, file upload, OpenRouter/OpenAI, admin dashboard, and
  deployment.
- Add a template changelog.
- Add template version metadata to manifests.

Acceptance criteria:

- Each recipe has setup, env vars, implementation notes, and verification.
- Generator can print the template version used for a generated project.

Verification:

```bash
make api-check-ai
make api-ci
```

## Risk Controls

- Commit after every passing verification batch.
- Keep generated caches, `.venv`, coverage files, and temporary projects out of
  commits.
- Before each commit, review `git status --short` and `git diff --stat`.
- Do not introduce Turborepo before a real JS/TS app or package exists.
- Do not delete backend direct commands after adding Turbo; `make api-ci` remains
  the backend source of truth.

## Recommended Next Action

1. Clean generated local artifacts if present:

```bash
find scripts/__pycache__ -type f -name '*.pyc' -delete 2>/dev/null || true
rmdir scripts/__pycache__ 2>/dev/null || true
make clean
```

2. Split and create the first two commits:

```bash
git status --short
git add scripts/doctor.py scripts/create_project.py docs/conventions docs/recipes apps/api/tests/core/test_template_scripts.py README.md Makefile
git commit -m "chore: add rapid template tooling"

git add -A
git reset docs/roadmap/remaining-template-execution-plan.md
git commit -m "refactor: move api into apps workspace"

git add docs/roadmap/remaining-template-execution-plan.md
git commit -m "docs: add remaining template execution roadmap"
```

Adjust staging if Git reports file moves differently after `git add -A`; the
important rule is that each commit remains reviewable and passes its listed
verification.
