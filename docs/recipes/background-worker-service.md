# Background Worker Service

Use this recipe when the app mainly accepts work and processes it asynchronously.

Keep:

- `app/worker.py`
- `app/crawler` for durable crawler jobs and business handlers
- Hatchet Cloud credentials in the worker and crawler-dispatcher environments
- PostgreSQL for durable job and result state
- Health endpoints for container orchestration

Consider removing:

- `app/auth` if the worker is never exposed as a user-facing API
- `app/users` if there is no account model

The crawler foundation already provides:

- Internal job creation with tenant-scoped idempotency
- Recoverable PostgreSQL-to-Hatchet dispatch
- Retry classification and durable job status
- A safe asynchronous HTTP client

Add a public submission endpoint only when a product needs one.

Verify:

```bash
make api-test-up
make api-ci
HATCHET_CLIENT_TOKEN=... make api-worker
HATCHET_CLIENT_TOKEN=... make api-crawler-dispatcher
```
