# Requirements Log

Track **active** requirements only. Git history is the archive — do not keep superseded or implemented entries here.

## Lifecycle rules

- **Add** an entry when a requirement is proposed or changed during a conversation.
- **Remove** an entry when the requirement is fully implemented and merged, or abandoned.
- **Split** into `.claude/requirements/<domain>.md` when any domain exceeds ~5 active entries; update this file to link to it.
- **Compress** multiple evolving entries for the same requirement into one "current state" entry.

## Format

```
### [Domain / Feature] — YYYY-MM-DD
**Requirement:** what was decided
**Change from:** (if modifying a prior requirement) what it replaced
**Reason:** why the change was made
```

---

<!-- Active requirements below -->

### Engineering Foundation — 2026-06-02
**Requirement:** Build a production-ready engineering foundation covering unified responses, business error codes, global exception handling, structured logging, environment-safe configuration, Alembic migration baseline, JWT session hardening, RBAC, i18n, and OpenAPI documentation standards.
**Change from:** New active requirement.
**Reason:** The project is evolving from a FastAPI starter template into a maintainable SaaS/backend foundation that future AI agents can implement phase by phase using `docs/engineering-foundation-requirements.md` and `docs/engineering-foundation-design.md`.

