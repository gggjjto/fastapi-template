# Storage and Modeling

Use this when reviewing data models, indexes, query paths, schema evolution, and retention.

## Modeling Heuristics

- Start from access patterns, not only entity nouns.
- Keep canonical facts normalized enough to enforce invariants.
- Denormalize only for clear read-path needs, and name the source that rebuilds the denormalized copy.
- Prefer append-only records for audit, ledger, event history, and compliance-sensitive facts.
- Avoid storing ambiguous state transitions without timestamps, actors, and idempotency keys.
- Model deletion and retention explicitly: hard delete, soft delete, anonymize, archive, or compact.

## PostgreSQL Defaults

- Use foreign keys for durable ownership where lifecycle coupling is real.
- Add unique constraints for business uniqueness; do not rely only on service-layer checks.
- Use partial indexes for sparse status flags or soft-delete patterns.
- Use composite indexes that match equality filters first, then ordering/range columns.
- Keep pagination deterministic with stable ordering and tie-breakers.
- Avoid offset pagination for large, frequently changing result sets; prefer keyset pagination where users scroll deep or data changes often.
- Check query plans for high-cardinality or high-traffic queries before optimizing speculative paths.

## Schema Evolution

- Prefer backward-compatible migrations:
  - Add nullable column or table.
  - Backfill in bounded batches.
  - Deploy code that writes both old and new shape if needed.
  - Switch reads.
  - Enforce constraints after data is clean.
  - Remove old shape later.
- Treat enum-like states carefully: old workers and clients may not understand new states.
- Make backfills resumable and idempotent.

## Review Smells

- Business invariant enforced only by "check then insert" outside a transaction.
- Cache becomes the only place a value exists.
- A table stores both current state and unbounded event history without clear query strategy.
- New endpoint needs several N+1 repository calls.
- Migration assumes production data is clean without a validation query.
- Derived table has no rebuild story.
