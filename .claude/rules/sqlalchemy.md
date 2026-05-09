---
description: SQLAlchemy ORM conventions and pitfalls for this FastAPI template
paths:
  - "app/**/*.py"
  - "tests/**/*.py"
---

## Query style

- Use SQLAlchemy 2.0 `select()` style, not legacy `session.query()`.
- Always `await` async queries; never call sync SQLAlchemy methods inside `async def`.

## N+1 queries

- Never access a relationship attribute inside a loop without eager loading — this fires one query per row.
- Use `selectinload` for one-to-many relationships (emits a second `IN` query, safe for large sets).
- Use `joinedload` for many-to-one / one-to-one relationships (single JOIN, efficient for small result sets).
- Default to lazy loading only for relationships that are never accessed in the current query path.

```python
# bad — N+1
users = await session.scalars(select(User))
for user in users:
    print(user.orders)  # fires one query per user

# good
users = await session.scalars(select(User).options(selectinload(User.orders)))
```

## Session lifetime

- Never store a `Session` / `AsyncSession` on a model, service, or module-level variable.
- Session is request-scoped via `DBSession` dependency; do not pass it between requests.
- Do not call `session.commit()` inside repository methods — commit at the service layer or let the request lifecycle handle it.

## Soft delete filter

- All normal queries must filter `Model.deleted_at.is_(None)` — see `.claude/rules/data-design.md`.
- Centralise this filter in repository base helpers; do not repeat it in every query.

## Avoid

- `session.execute(text(...))` for queries that can be expressed with ORM constructs.
- Accessing `session` after the request context has closed (common in background tasks — use a new session).
- Relying on `expire_on_commit=True` (default) to refresh objects after commit inside the same request; refresh explicitly if needed.
- Bulk inserts via repeated `session.add()` in a loop — use `session.bulk_insert_mappings()` or `insert()` for large sets.
