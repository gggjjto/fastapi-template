# Rapid Development Template

A personal rapid-development template workspace, starting with a
production-minded FastAPI backend in `apps/api` and designed to grow into
frontend, worker, CLI, SDK, and automation templates when needed.

## Why this template

- Domain-oriented structure for clean growth (`auth`, `users`, `core`)
- JWT auth, RBAC, and unified API response/error contracts
- Redis + Arq job queue and cron support
- Structured logging, request-id tracing, rate limiting
- Ready for production hardening and CI-backed workflows
- i18n error messages and async SQLAlchemy + Alembic setup
- Recipes and scripts for spinning up new projects from the template

## Get started

```bash
make api-install
cp apps/api/.env.example apps/api/.env
make api-dev
```

Or launch the full stack:

```bash
cd apps/api
docker compose up
```

API docs are available at `http://127.0.0.1:8000/docs`.

## Create a new project

Check local prerequisites:

```bash
make doctor
```

Create a copy of the template with project naming applied:

```bash
make create-project name=my-saas-api target=../my-saas-api
```

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
