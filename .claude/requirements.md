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
**Decisions:**
- Response envelope adopts **Option A**: `ApiResponse.code` is a stable **string** business code (`"OK"` / `"USER_NOT_FOUND"` …) plus a new `request_id` field — not the transitional int+`error_code` shape. Chosen because the template has no external API consumers yet.
- Implementation proceeds **phase by phase**; Phase 1 (error contract + global exception handling) is delivered first, the rest only after sign-off.
**Phase 1 status (done in code, pending integration-test run):** string error codes, enhanced `DomainError` hierarchy, global `DomainError`/unhandled-`Exception` handlers, `request_id` in envelopes, routers no longer hand-translate domain exceptions, `valid_user_id` raises domain `UserNotFound`.

