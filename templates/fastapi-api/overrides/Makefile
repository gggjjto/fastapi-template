.PHONY: help doctor create-project api-install api-dev api-lint api-lint-fix api-format \
        api-format-check api-typecheck api-test api-cov api-ci api-check-ai api-test-up \
        api-test-down api-migrate api-revision api-docker-build api-docker-run clean

help:
	@echo "Available API template targets:"
	@echo "  doctor              Check local development prerequisites"
	@echo "  create-project      Create a new project: make create-project name=my-app target=../my-app"
	@echo "  api-install         Install API dependencies"
	@echo "  api-dev             Run API dev server with --reload"
	@echo "  api-lint            Run API ruff check"
	@echo "  api-lint-fix        Run API ruff check --fix"
	@echo "  api-format          Run API ruff format"
	@echo "  api-format-check    Check API formatting"
	@echo "  api-typecheck       Run API mypy"
	@echo "  api-check-ai        Guard .agents as the AI workflow source of truth"
	@echo "  api-test            Run API pytest (requires api-test-up services)"
	@echo "  api-cov             Run API pytest with coverage"
	@echo "  api-ci              Run API CI checks locally"
	@echo "  api-test-up         Start API PostgreSQL + Redis test containers"
	@echo "  api-test-down       Stop API test containers"
	@echo "  api-migrate         Apply API Alembic migrations"
	@echo "  api-revision m=...  Autogenerate API Alembic revision"
	@echo "  api-docker-build    Build API Docker image"
	@echo "  api-docker-run      Run API Docker image on :8000"
	@echo "  clean               Remove API caches"

doctor:
	python3 scripts/doctor.py --template "$(or $(template),fastapi-api)"

create-project:
	python3 scripts/create_project.py "$(name)" "$(target)" --template "$(or $(template),fastapi-api)"

api-install:
	$(MAKE) -C apps/api install

api-dev:
	$(MAKE) -C apps/api dev

api-lint:
	$(MAKE) -C apps/api lint

api-lint-fix:
	$(MAKE) -C apps/api lint-fix

api-format:
	$(MAKE) -C apps/api format

api-format-check:
	$(MAKE) -C apps/api format-check

api-typecheck:
	$(MAKE) -C apps/api typecheck

api-check-ai:
	$(MAKE) -C apps/api check-ai

api-test:
	$(MAKE) -C apps/api test

api-cov:
	$(MAKE) -C apps/api cov

api-ci:
	$(MAKE) -C apps/api ci

api-test-up:
	$(MAKE) -C apps/api test-up

api-test-down:
	$(MAKE) -C apps/api test-down

api-migrate:
	$(MAKE) -C apps/api migrate

api-revision:
	$(MAKE) -C apps/api revision m="$(m)"

api-docker-build:
	$(MAKE) -C apps/api docker-build

api-docker-run:
	$(MAKE) -C apps/api docker-run

clean:
	$(MAKE) -C apps/api clean
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
