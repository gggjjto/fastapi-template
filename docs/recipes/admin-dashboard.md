# Admin Dashboard

Use this recipe when the project needs internal operations screens for users,
roles, jobs, audits, or support workflows.

## Setup

```bash
make api-install
cp apps/api/.env.example apps/api/.env
```

If using the existing `apps/web` workspace as the admin UI, keep admin routes in
a clearly named route group and protect the API with RBAC permissions.

## Env Vars

```bash
APP_CORS_ORIGINS=http://localhost:3000
APP_JWT_SECRET=
APP_ADMIN_BOOTSTRAP_EMAIL=
```

Use bootstrap variables only for local setup or one-time seed scripts; avoid
long-lived privileged defaults.

## Implementation Notes

- Keep admin API endpoints under a dedicated domain or route prefix.
- Require explicit permissions for every privileged action.
- Add audit logging for role changes, impersonation, destructive actions, and
  data exports.
- Prefer server-side pagination and filtering for operational tables.
- Avoid exposing broad search endpoints without rate limits and permission
  checks.
- In the web app, use a dense dashboard layout rather than a marketing page.

## Verification

```bash
make api-lint
make api-format-check
make api-typecheck
make api-test
pnpm lint
pnpm typecheck
pnpm build
```

Add tests for unauthenticated access, forbidden access, successful admin access,
and audit-log writes for sensitive operations.
