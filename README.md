# Rapid Development Template

A personal rapid-development template workspace with a production-minded
FastAPI backend in `apps/api`, a Next.js frontend in `apps/web`, and
Turborepo orchestration for growing into workers, CLIs, SDKs, and automation
templates when needed.

## Why this template

- Domain-oriented structure for clean growth (`auth`, `users`, `core`)
- JWT auth, RBAC, and unified API response/error contracts
- Redis caching plus Hatchet Cloud background tasks
- Structured logging, request-id tracing, rate limiting
- Ready for production hardening and CI-backed workflows
- i18n error messages and async SQLAlchemy + Alembic setup
- Recipes for adapting the repository to common project shapes
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
make api-worker  # requires HATCHET_CLIENT_TOKEN
make api-crawler-dispatcher  # requires HATCHET_CLIENT_TOKEN
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
make harness-check
# Optional: runs disposable-workspace live coding-agent evaluations
make harness-eval
```

Start a project by cloning the repository and replacing its Git history:

```bash
git clone <repository-url> my-saas-api
cd my-saas-api
rm -rf .git
git init
```

Then initialize it:

```bash
make api-install
cp apps/api/.env.example apps/api/.env
make api-test-up
make api-ci
```

Current architecture, contracts, and operating guides live in
[`docs/`](./docs/README.md).

## AI workflow

See `.agents/` for mandatory workflow guidance and [`docs/README.md`](./docs/README.md)
for documentation authority and lifecycle. Keep changes minimal and
behavior-focused, and add tests when behavior changes.

## Contribute

Issues and PRs are welcome. PRs should follow project conventions and include the necessary tests.

## License

MIT — see [LICENSE](./LICENSE).
