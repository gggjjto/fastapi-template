# FastAPI AI Template

A compact FastAPI backend template optimized for AI-assisted development.

## Why this template

- Domain-oriented structure for clean growth (`auth`, `users`, `core`)
- JWT auth, RBAC, and unified API response/error contracts
- Redis + Arq job queue and cron support
- Structured logging, request-id tracing, rate limiting
- Ready for production hardening and CI-backed workflows
- i18n error messages and async SQLAlchemy + Alembic setup

## Get started

```bash
uv sync --dev
cp .env.example .env
uv run uvicorn app.main:app --reload
```

Or launch the full stack:

```bash
docker compose up
```

API docs are available at `http://127.0.0.1:8000/docs`.

## AI workflow

See `.agents/` for mandatory conventions and local AI workflow guidance. Keep changes minimal and behavior-focused, and add tests when behavior changes.

## Contribute

Issues and PRs are welcome. PRs should follow project conventions and include the necessary tests.

## License

MIT — see [LICENSE](./LICENSE).
