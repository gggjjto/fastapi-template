# Hatchet Crawler

Use Hatchet as the orchestration layer for future crawlers. Keep fetching,
parsing, and persistence in the crawler domain; store results in PostgreSQL or
object storage rather than Hatchet.

## Task input

Pass identifiers and routing metadata only:

```python
class CrawlTaskInput(BaseModel):
    crawl_job_id: UUID
    tenant_id: UUID
    target_url_id: UUID
    target_host: str
```

Do not pass HTML, credentials, cookies, proxy secrets, or other large payloads.
Workers should load authorized data by ID and persist progress idempotently.

## Execution policy

- Apply concurrency and rate limits by `target_host` so one site cannot consume
  the worker or receive excessive traffic.
- Retry transient network failures with exponential backoff. Do not retry HTTP
  4xx responses, validation failures, or operations that are not idempotent.
- Run blocking browser automation on a dedicated worker with separate capacity;
  keep ordinary HTTP crawlers async.
- Keep `HATCHET_CLIENT_TOKEN` in the worker environment only. Never log it or
  store it in task input.

See Hatchet's official guidance for [concurrency](https://docs.hatchet.run/v1/concurrency),
[rate limits](https://docs.hatchet.run/v1/rate-limits), and
[retry policies](https://docs.hatchet.run/v1/retry-policies).
