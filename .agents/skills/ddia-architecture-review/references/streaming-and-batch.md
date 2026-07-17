# Streaming and Batch

Use this when reviewing queues, workers, events, scheduled jobs, retries, ordering, backfills, or pipelines.

## Queue and Worker Design

- Make jobs idempotent by job key, business key, or destination key.
- Store enough state to retry after process crash.
- Keep payloads small; store large canonical data in PostgreSQL and pass identifiers.
- Bound retries and define poison-message handling.
- Emit metrics for enqueue count, success, failure, retry, dead-letter, and lag.
- Version job payloads if old workers may process new jobs or vice versa.

## Ordering and Deduplication

- Avoid relying on global ordering unless the queue actually provides it.
- If ordering matters, define the ordering scope: per user, account, aggregate, partition, or stream.
- Use sequence numbers, version checks, or monotonic timestamps for per-entity ordering.
- Deduplicate at the side-effect boundary, not only at message receipt.

## Backfills and Batch Jobs

- Make backfills resumable, idempotent, and bounded.
- Process in stable order with checkpoints.
- Rate-limit writes and external calls.
- Separate dry-run validation from mutation.
- Record progress and error samples.
- Plan rollback or forward-fix before running.

## Event Design

- Prefer events that describe durable facts, not vague commands.
- Include event id, schema version, occurred_at, actor or system source, and correlation id where useful.
- Avoid stuffing mutable snapshots into events unless consumers need that exact historical snapshot.
- Document compatibility expectations for adding fields, removing fields, and changing meaning.

## Review Smells

- Worker assumes a database row still exists without handling deletion.
- Retry sends duplicate email/payment/webhook.
- Scheduled job scans an unbounded table every minute.
- Backfill code cannot resume after interruption.
- Event consumers cannot tell whether an event is old, duplicate, or incompatible.
