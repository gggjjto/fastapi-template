.PHONY: help install dev lint lint-fix format format-check typecheck test cov ci \
        test-up test-down migrate revision docker-build docker-run clean

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies (including dev)"
	@echo "  dev            Run dev server with --reload"
	@echo "  lint           Run ruff check"
	@echo "  lint-fix       Run ruff check --fix"
	@echo "  format         Run ruff format"
	@echo "  format-check   Check formatting (CI-friendly)"
	@echo "  typecheck      Run mypy"
	@echo "  test           Run pytest (requires test-up services)"
	@echo "  cov            Run pytest with coverage"
	@echo "  ci             Run all CI checks locally (lint + format-check + typecheck + cov)"
	@echo "  test-up        Start PostgreSQL + Redis containers for tests"
	@echo "  test-down      Stop and remove test containers"
	@echo "  migrate        Apply Alembic migrations"
	@echo "  revision m=... Autogenerate Alembic revision"
	@echo "  docker-build   Build Docker image"
	@echo "  docker-run     Run Docker image on :8000"
	@echo "  clean          Remove caches and build artefacts"

install:
	uv sync --dev

dev:
	uv run uvicorn app.main:app --reload

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy app

test:
	uv run pytest

cov:
	uv run pytest --cov --cov-report=term-missing --cov-report=xml

ci: lint format-check typecheck cov

test-up:
	docker compose -f docker-compose.test.yml up -d --wait

test-down:
	docker compose -f docker-compose.test.yml down -v

migrate:
	uv run alembic upgrade head

revision:
	uv run alembic revision --autogenerate -m "$(m)"

docker-build:
	docker build -t fastapi-template:local .

docker-run:
	docker run --rm -p 8000:8000 \
		-e APP_JWT_SECRET=local-dev \
		-e APP_DATABASE_URL=sqlite+aiosqlite:///./app.db \
		-e APP_DB_CREATE_TABLES_ON_STARTUP=true \
		fastapi-template:local

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov \
		dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
