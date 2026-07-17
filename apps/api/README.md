# FastAPI API Template

Production-minded FastAPI backend template for the rapid-development workspace.

## Get Started

```bash
uv sync --dev
cp .env.example .env
make test-up
make ci
make dev
```

API docs are available at `http://127.0.0.1:8000/docs` when the development
server is running.

## Quality Gate

```bash
make lint
make format-check
make typecheck
make check-ai
make test
```
