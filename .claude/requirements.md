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
- Implementation proceeds **phase by phase**; each phase is a separate commit, the next only after sign-off.
- **Phase 3 auth decisions:** access tokens stay stateless/short-lived (no per-request DB check); `logout` revokes the current session (refresh_token in body) and `logout-all` revokes all sessions (requires auth); detected refresh-token reuse revokes **all** of the user's sessions.
- **Phase 4 RBAC decisions:** global RBAC (roles/permissions/user_roles/role_permissions, `resource:action`); permission catalog + `admin`(all)/`user`(none) roles seeded idempotently at startup (`app/auth/seed.py`), not in the migration; **first registered user becomes admin**, others get `user`; `GET /users` + `GET /users/{id}` require `users:read`, registration stays public.

**Progress (done + green via `make ci`):**
- Phase 1 — error contract: string error codes, `DomainError` hierarchy, global `DomainError`/unhandled handlers, `request_id` in envelopes, routers no longer hand-translate.
- Phase 2 — config + migration: production `Settings` fail-fast validation; initial Alembic migration (`users`).
- Phase 3 — JWT sessions: `auth_sessions` table + migration, refresh rotation, reuse detection, logout / logout-all.
- Phase 4 — RBAC: roles/permissions tables + migration, startup seeding, first-user-admin, `RequirePermission`, protected user list/detail.
- Phase 5 — i18n + OpenAPI: `app/core/i18n.py` + `locales/{en-US,zh-CN}.json`, domain-error messages localized via `Accept-Language` (default `APP_DEFAULT_LOCALE=en-US`); `app/core/openapi.py` `error_responses()` + `ErrorResponse` applied across routers.

**Remaining:** Phase 6 (logging hardening: access-log fields, sensitive-data redaction, OpenTelemetry prep).

