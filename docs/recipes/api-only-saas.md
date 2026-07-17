# API-only SaaS

Use this recipe when the product is mostly an HTTP API with users, auth, roles,
background jobs, and production-oriented observability.

Keep:

- `app/auth`
- `app/users`
- `app/core`
- `app/db`
- `app/worker.py`
- PostgreSQL, Redis, Arq, Sentry, rate limiting, i18n, and request IDs

Add next:

- Product-specific domains under `app/<domain>/`
- Billing integration if the SaaS is paid
- Deployment-specific health checks and release docs

Verify:

```bash
make api-test-up
make api-ci
```
