# Review Checklists

Use these prompts to structure a data-intensive architecture review.

## Intake Questions

- What is the durable source of truth?
- Which business invariants must never be violated?
- Which reads can be stale, and for how long?
- What is the expected write rate, read rate, and cardinality growth?
- What is the largest fanout path?
- What happens when a request, transaction, job, or external call times out?
- Can clients retry safely?
- Is there a manual or automated recovery path?

## Design Matrix Columns

- Correctness: preserves invariants under concurrency and retries.
- Simplicity: minimizes moving parts and special cases.
- Latency: meets user-facing and worker-facing timing needs.
- Throughput: handles normal and burst traffic.
- Operability: easy to observe, recover, migrate, and debug.
- Cost: storage, compute, query, and operational cost.
- Evolvability: handles schema changes and new access patterns.

## Failure Mode Sweep

- Duplicate request, duplicate event, duplicate job.
- Lost update or write skew.
- Stale cache or stale replica read.
- Queue backlog or poison message.
- Partial commit across database and external system.
- Hot row, hot partition, or hot cache key.
- Slow query, missing index, unbounded pagination.
- Backfill corrupts live data or violates rate limits.
- Schema change breaks old workers or clients.
- Metrics report success while derived data is missing.

## Recommended Output

```text
Recommendation
- Choose ...
- Because ...

Options
| Option | Strength | Weakness | Best fit |

Risks
- P1: ...
- P2: ...

Implementation
- API:
- Service:
- Repository/database:
- Worker/cache:

Verification
- Tests:
- Metrics/logs:
- Rollout:
```
