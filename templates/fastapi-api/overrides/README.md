# Rapid Development Template

A generated FastAPI backend project from the rapid development template.

## Why this template

- Domain-oriented structure for clean growth (`auth`, `users`, `core`)
- JWT auth, RBAC, and unified API response/error contracts
- Redis + Arq job queue and cron support
- Structured logging, request-id tracing, rate limiting
- Ready for production hardening and CI-backed workflows
- i18n error messages and async SQLAlchemy + Alembic setup

## Get started

```bash
make api-install
cp apps/api/.env.example apps/api/.env
make api-test-up
make api-dev
```

Or launch the full API stack:

```bash
cd apps/api
docker compose up
```

API docs are available at `http://127.0.0.1:8000/docs`.

## Validation

```bash
make api-lint
make api-format-check
make api-typecheck
make api-test
make api-ci
make harness-check
# Optional model-backed evaluation
make harness-eval
```

## AI workflow

See `.agents/` for mandatory conventions and local AI workflow guidance. Keep
changes minimal and behavior-focused, and add tests when behavior changes.

## License

MIT - see [LICENSE](./LICENSE).
