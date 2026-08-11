# Template Changelog

## fastapi-api 0.1.0

Initial productized template baseline.

- FastAPI backend under `apps/api` with auth, RBAC, PostgreSQL, Redis, Hatchet, Docker, and CI quality gates.
- Template manifest with capability metadata and validation for `--with-*` flags.
- API-only generation overrides for README, Makefile, CI, and Dependabot.
- Template-aware doctor profile through `scripts/doctor.py --template fastapi-api`.
- Recipes for common backend, integration, and deployment shapes.
