# Replication and Partitioning

Use this when reviewing replicas, derived data, sharding, fanout, hot keys, or growth limits.

## Derived Copies

For every derived copy, record:

- Source of truth.
- Transformation logic.
- Freshness expectation.
- Rebuild process.
- Drift detection.
- Owner and alerting signal.

Derived copies include caches, read models, search indexes, analytics tables, materialized views, and exported files.

## Replica and Freshness Questions

- Can this read be served from a replica or cache?
- What user-visible behavior occurs after a write?
- Does read-your-writes matter?
- How will lag be measured?
- What happens when a replica is stale or unavailable?

## Partitioning Questions

- What key determines data placement?
- Is tenant, user, organization, region, or time the natural boundary?
- Which queries become cross-partition?
- Which keys can become hot?
- Can a large tenant be split later?
- How are global uniqueness and ordering handled?

## Fanout Strategies

- Fanout-on-write: faster reads, higher write cost, harder recovery.
- Fanout-on-read: simpler writes, slower reads, possible repeated work.
- Hybrid: precompute for hot or bounded cases, compute on read for long tail.

Choose based on write rate, read frequency, freshness needs, and rebuild complexity.

## Review Smells

- Partition key chosen before access patterns are known.
- "Just shard it later" with no stable routing key.
- A single tenant or user can dominate a partition.
- A derived view has no reconciliation job.
- Cache key cardinality can grow without TTL or eviction planning.
