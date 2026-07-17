---
name: ddia-architecture-review
description: Apply Designing Data-Intensive Applications style architecture review to backend and distributed-system work. Use when designing, reviewing, or changing data-intensive features involving databases, data models, indexes, caches, Redis, PostgreSQL, queues, workers, events, replication, partitioning, transactions, consistency, streaming, batch jobs, migrations, audit logs, analytics, reliability, or tradeoff-heavy storage decisions.
---

# DDIA Architecture Review

Use this skill to turn data-intensive system design questions into explicit engineering tradeoffs, failure-mode checks, and verification steps. Do not quote or reproduce book text; use original engineering guidance inspired by durable distributed-systems principles.

## Review Workflow

1. Restate the workload in concrete terms:
   - Primary user journey or business invariant.
   - Reads, writes, background jobs, and external integrations.
   - Data growth estimate, retention, fanout, and hot-key risks.
   - Latency, freshness, durability, and recovery expectations.

2. Classify the system shape:
   - Transactional API, analytical/reporting path, cache-assisted API, event-driven workflow, stream processor, batch job, audit trail, search/read model, or mixed system.
   - Identify the source of truth and every derived copy.

3. Build a decision matrix:
   - Compare at least two plausible designs.
   - Score them on correctness, operational complexity, observability, migration risk, cost, and developer ergonomics.
   - Call out the simplest design that preserves the required invariants.

4. Review the data path:
   - Data model and access patterns.
   - Indexes, query shape, pagination, and lock contention.
   - Transaction boundaries and idempotency.
   - Cache invalidation or freshness strategy.
   - Queue/event semantics, retries, ordering, and deduplication.

5. Name failure modes:
   - Partial failure, timeout, duplicate delivery, lost update, stale read, overload, thundering herd, schema drift, reprocessing, backfill, poison message, and bad deployment.
   - For each serious failure mode, state the detection signal and recovery action.

6. End with implementation guidance:
   - Recommended design and rejected alternatives.
   - Tests to write, including integration and concurrency tests where relevant.
   - Metrics/logs/traces/alerts to add.
   - Migration or rollout sequence.
   - ADR points if the decision affects architecture, data ownership, consistency, or operations.

## Project Defaults

For this FastAPI template, prefer these defaults unless the user gives stronger constraints:

- Treat PostgreSQL as the durable source of truth.
- Use Redis for cache, rate limiting, ephemeral coordination, and Arq queues; do not store canonical business facts only in Redis.
- Keep HTTP handlers thin; put data decisions in domain service/repository layers.
- Make mutations idempotent when they enqueue jobs, call external systems, or can be retried by clients.
- Use Alembic migrations for persistent schema changes.
- Add integration tests using the existing PostgreSQL and Redis test containers for cross-component behavior.
- Document durable architectural decisions with an ADR when changing consistency, data ownership, or recovery behavior.

## Reference Loading

Load only the reference files needed for the current problem:

- `references/review-checklists.md`: universal review prompts and output format.
- `references/storage-and-modeling.md`: data modeling, indexes, access patterns, retention, and schema evolution.
- `references/transactions-consistency.md`: transactions, isolation, idempotency, optimistic concurrency, and invariants.
- `references/replication-partitioning.md`: replicas, derived data, sharding, hot keys, fanout, and resharding.
- `references/streaming-and-batch.md`: queues, streams, workers, retries, ordering, deduplication, backfills, and batch jobs.
- `references/fastapi-postgres-redis-patterns.md`: concrete patterns for this repository's FastAPI, PostgreSQL, Redis, and Arq stack.

## Response Shape

For design reviews, prefer:

1. **Recommendation**: one clear recommendation with the core reason.
2. **Tradeoffs**: short table comparing the main options.
3. **Risks**: correctness and operations risks, ordered by severity.
4. **Implementation Notes**: changes by layer or component.
5. **Verification**: tests, metrics, and rollout checks.

For small code changes, keep the review lightweight and focus on the specific data path being edited.
