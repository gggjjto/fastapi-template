---
description: AI fast-development workflow for this FastAPI template — applied globally
globs: "**/*"
---

## AI fast-development loop

Use this workflow for feature work:

1. Locate the closest existing domain and mirror its patterns.
2. Propose the smallest useful change before editing when requirements are unclear.
3. Change code in domain order: `schemas.py` → `models.py` → `repository.py` → `service.py` → `dependencies.py` → `router.py` → tests.
4. Keep routers thin. Business decisions belong in services; database queries belong in repositories.
5. Add or update tests for behavior changes. Prefer integration tests over mocks.
6. Check documentation and update the smallest relevant file when behavior, setup, API, CI, or workflow changes.
7. Run the narrowest useful verification first, then broader gates when finishing.

## Prompt shape that works well

When asking AI to implement a feature, include:

- Domain name and target endpoint or behavior.
- Authentication/authorization requirement.
- Data model fields and validation rules.
- Expected success response and important error cases.
- Whether a database migration is expected.

Example:

```text
Add an orders domain with POST /orders.
Authenticated users can create orders with product_id and quantity.
Use ApiResponse, domain exceptions, repository queries, and integration tests.
Follow CLAUDE.md and existing users/auth patterns.
```

## Default assumptions

- Prefer existing local helpers over new dependencies.
- Do not add infrastructure unless the feature needs it now.
- Follow `.claude/rules/docs-maintenance.md` for documentation updates.
