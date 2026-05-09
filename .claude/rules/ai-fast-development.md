---
description: AI fast-development workflow for this FastAPI template
paths:
  - "app/**"
  - "tests/**"
  - "alembic/**"
---

## AI fast-development loop

Use this workflow for feature work:

1. Locate the closest existing domain and mirror its patterns.
2. **If requirements are unclear, ask targeted questions first — do not start writing code until the key decisions (fields, auth, error cases, migration) are resolved.**
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
- **When adding code to an existing file, clean up inconsistencies in the surrounding code rather than layering new code on top of messy existing code.**
- Follow karpathy-guidelines when writing code: state assumptions explicitly, touch only what is required, add no speculative features, and define a verifiable success criterion before starting.
- **When requirements change, delete or replace the old logic — do not add fallback / compatibility shims to hedge between the old and new behavior. If the new requirement is correct, the old path is wrong; keeping it silently is a bug, not safety.**
- **Maintain `.claude/requirements.md`**: when a requirement is proposed, clarified, or changed during a conversation, append an entry to that file (domain, decision, reason, status). For key decisions, also write a project-type memory file.

