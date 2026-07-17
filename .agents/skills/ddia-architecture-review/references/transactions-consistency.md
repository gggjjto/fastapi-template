# Transactions and Consistency

Use this when reviewing correctness under concurrency, retries, and partial failure.

## Invariant First

Write down the invariant before choosing isolation or locking. Examples:

- A user email is globally unique.
- A balance must never go below zero.
- A refresh token can be used once after rotation.
- A job may be retried, but its external side effect must happen once.

## Common Patterns

- Use database constraints for uniqueness and referential integrity.
- Use a single database transaction when all changed facts live in PostgreSQL.
- Use optimistic concurrency with a version column for collaborative or long-lived updates.
- Use row-level locks for short, high-value critical sections; keep locked work minimal.
- Use idempotency keys for client retries and queued side effects.
- Use an outbox table when a database commit must reliably lead to an event or external call.
- Use compensating actions only when true atomicity is impossible and the business can tolerate reversal.

## Isolation Review

- Read committed is often fine for simple CRUD plus constraints.
- Repeatable read or serializable may be needed when decisions depend on a set of rows.
- Locks may be clearer than higher isolation when the conflict set is small and obvious.
- Retry serialization failures explicitly when using serializable transactions.

## Redis and Consistency

- Treat Redis as non-durable unless configured and operated for durability.
- Use TTLs for cached data unless there is a strong reason not to.
- Prefer cache-aside for simple reads: read cache, miss to PostgreSQL, set cache.
- Invalidate or update cache immediately after successful database commit.
- For distributed locks, include expirations and fencing tokens when stale lock holders can cause damage.

## Review Smells

- External API call inside a database transaction.
- Queue enqueue happens before database commit without recovery logic.
- Retry can create duplicate rows, emails, charges, or events.
- A read-modify-write path has no constraint, lock, version, or retry.
- The design promises "exactly once" without naming the idempotency boundary.
