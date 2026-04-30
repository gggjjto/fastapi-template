# Add Domain

Use this workflow to add a new FastAPI business domain.

## Inputs

Ask for any missing critical details:

- Domain name.
- Main entities and fields.
- Required endpoints.
- Auth/permission rules.
- Whether persistent database tables are needed.

## Workflow

1. If the design is unclear, use `fastapi-architect` to plan the domain shape first (read-only planning step — skip for straightforward domains).
2. Follow `.claude/rules/fastapi-domain-scaffold.md`.
3. Create domain files only as needed:
   - `constants.py`
   - `exceptions.py`
   - `models.py`
   - `repository.py`
   - `schemas.py`
   - `service.py`
   - `router.py`
   - `dependencies.py` only for resource loading or guards
4. Register the router in `app/router.py`.
5. If models changed, import them in `app/db/session.py` and `alembic/env.py`.
6. Add integration tests under `tests/<domain>/`.
7. Run docs maintenance check.
8. Run focused verification, then broader gates.

## Verification

```bash
uv run pytest tests/<domain>/ -v
uv run ruff check .
uv run mypy app
```

If database schema changed, generate and review a migration:

```bash
make revision m="<describe change>"
```

## Output

Return:

1. Files created or changed.
2. Endpoints added.
3. Tests and checks run.
4. Any migration or documentation follow-up.
