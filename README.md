# Rapid Development Template

A personal rapid-development template workspace with a production-minded
FastAPI backend in `apps/api`, a Next.js frontend in `apps/web`, and
Turborepo orchestration for growing into workers, CLIs, SDKs, and automation
templates when needed.

## Why this template

- Domain-oriented structure for clean growth (`auth`, `users`, `core`)
- JWT auth, RBAC, and unified API response/error contracts
- Redis + Arq job queue and cron support
- Structured logging, request-id tracing, rate limiting
- Ready for production hardening and CI-backed workflows
- i18n error messages and async SQLAlchemy + Alembic setup
- Recipes and scripts for spinning up new projects from the template
- Next.js App Router web workspace with pnpm + Turborepo coordination
- Shared JS/TS config package for workspace apps

## Get started

```bash
pnpm install
make api-install
cp apps/api/.env.example apps/api/.env
make api-test-up
make dev
```

Run API or web independently when you only need one side:

```bash
make api-dev
make web-dev
```

Or launch the full stack:

```bash
cd apps/api
docker compose up
```

API docs are available at `http://127.0.0.1:8000/docs`.
The web app runs at `http://localhost:3000`.

## Workspace commands

```bash
make lint         # Turbo lint across workspace packages
make typecheck    # Turbo typecheck across workspace packages
make test         # Turbo test; API tests require make api-test-up
make build        # Turbo build across workspace packages
make api-ci       # Backend CI checks only
make web-build    # Frontend build only
```

Shared workspace packages live under `packages/`. Start with
`packages/config` for reusable TypeScript and ESLint defaults; add SDK/UI
packages only when an app actually imports them.

## Create a new project

Check local prerequisites:

```bash
make doctor
```

Create a copy of the template with project naming applied:

```bash
make create-project name=my-saas-api target=../my-saas-api
```

Template capability flags are available for planning future slimmer variants.
They validate combinations and print selected capabilities while the current
`fastapi-api` template still includes the production-minded backend surface by
default:

```bash
python3 scripts/create_project.py my-api ../my-api --with-auth --with-rbac
python3 scripts/create_project.py jobs-api ../jobs-api --with-redis --with-worker
```

See [`templates/fastapi-api/OPTIONS.md`](./templates/fastapi-api/OPTIONS.md)
for the exact files and environment variables associated with each option.

Then initialize the generated project:

```bash
cd ../my-saas-api
make api-install
cp apps/api/.env.example apps/api/.env
make api-test-up
make api-ci
```

Recipes for common project shapes live in [`docs/recipes`](./docs/recipes/README.md).

## AI workflow

See `.agents/` for mandatory conventions and local AI workflow guidance. Keep changes minimal and behavior-focused, and add tests when behavior changes.

## Contribute

Issues and PRs are welcome. PRs should follow project conventions and include the necessary tests.

## License

MIT — see [LICENSE](./LICENSE).
