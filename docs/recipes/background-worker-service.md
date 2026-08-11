# Background Worker Service

Use this recipe when the app mainly accepts work and processes it asynchronously.

Keep:

- `app/worker.py`
- Hatchet Cloud credentials in the worker environment
- PostgreSQL for durable job and result state
- Health endpoints for container orchestration

Consider removing:

- `app/auth` if the worker is never exposed as a user-facing API
- `app/users` if there is no account model

Add next:

- Job submission endpoints
- Idempotency keys for externally triggered jobs
- Retry and dead-letter conventions
- Job status persistence if clients need progress updates

Verify:

```bash
make api-test-up
make api-ci
HATCHET_CLIENT_TOKEN=... make api-worker
```
