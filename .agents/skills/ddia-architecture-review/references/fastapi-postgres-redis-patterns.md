# FastAPI, PostgreSQL, Redis, and Arq Patterns

Use this for architecture review in this repository.

## Layering

- Router: parse HTTP inputs, inject dependencies, return DTOs.
- Service: enforce business invariants, transaction boundaries, idempotency, and domain errors.
- Repository: own SQLAlchemy queries, locks, constraints, pagination, and query-specific helpers.
- Worker: execute asynchronous side effects and scheduled maintenance.

## PostgreSQL

- Put business uniqueness in constraints and translate integrity errors to domain exceptions.
- Keep transaction scopes in service methods where multiple repository operations form one business action.
- Add migrations for persistent changes; use staged migrations for risky production changes.
- Add repository tests for non-trivial query semantics.

## Redis Cache

- Use cache-aside for read-heavy derived values.
- Include versioned key prefixes when data shape changes.
- Set TTLs by default.
- Invalidate after database commit when correctness depends on freshness.
- Do not make Redis the only source of durable business state.

## Arq Workers

- Enqueue jobs after durable state exists.
- Prefer passing identifiers to jobs, not full mutable object snapshots.
- Make job functions idempotent and safe under retry.
- Register new jobs in `app/worker.py`.
- Test queue-facing behavior with Redis enabled in integration tests.

## Testing Expectations

- Use existing integration style with real PostgreSQL and Redis.
- Add concurrency tests when changing locks, uniqueness, session rotation, inventory, balances, or any invariant under race.
- Add failure-path tests for retries, stale cache, missing rows, and duplicate jobs where relevant.
- Prefer dependency overrides at API boundaries rather than monkeypatching internals.

## Observability

- Log correlation identifiers for request-to-worker flows.
- Track queue lag, retries, and dead-letter counts.
- Track cache hit rate and stale/miss behavior for important caches.
- Track slow queries and rows scanned for new high-traffic access patterns.
