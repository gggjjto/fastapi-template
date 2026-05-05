# Database Change

Use this workflow for database model, schema, and migration changes.

## Workflow

1. Confirm the data model change and backwards compatibility needs.
2. Update the ORM model in the owning domain.
3. Register new models in:
   - `app/db/session.py`
   - `alembic/env.py`
4. Generate an Alembic revision with **autogenerate**: `make revision m="<describe change>"` — do not add new revision `.py` files by hand.
5. Review the generated migration for static, reversible operations.
6. Update repositories/services/tests that depend on the schema.
7. Run docs maintenance check for config, setup, or API impacts.

## Migration commands

```bash
make revision m="<describe change>"
make migrate
```

For CI-style validation:

```bash
uv run alembic upgrade head
uv run alembic downgrade base
```

## Guardrails

- Always create revisions via `make revision m="..."` (Alembic `--autogenerate`); only **edit** the generated file when autogenerate misses something (data migrations, partial indexes, etc.).
- Do not hand-edit migration state to hide drift.
- Do not rely on dynamic data to define migration structure.
- Do not add model fields without schema/test updates when API output changes.

## Output

Return:

1. Model changes.
2. Migration file created and reviewed.
3. Tests/checks run.
4. Compatibility notes.
