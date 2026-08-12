# Hatchet Crawler

The crawler foundation keeps business handlers separate from dispatch,
persistence, retry, and network safety. Add new crawler behavior under
`app/crawler/handlers/`; the worker discovers handler modules at startup.

## Runtime flow

1. `CrawlerService` creates or reuses a PostgreSQL job with pending execution
   and dispatch states.
2. `make api-crawler-dispatcher` leases pending rows and submits Hatchet runs.
3. `make api-worker` executes the registered handler and stores its structured
   result in PostgreSQL JSONB.

The API does not import Hatchet and starts without `HATCHET_CLIENT_TOKEN`.
Only the dispatcher and worker require the token.

## Add a crawler

Create one module under `app/crawler/handlers/` and register an async handler:

```python
@register_handler("product-page")
async def product_page(target: CrawlTarget, client: SafeAsyncCrawlerClient) -> dict[str, object]:
    response = await client.fetch(target.target_url)
    return {"status_code": response.status_code}
```

The platform discovers the module at worker startup and owns job state,
idempotency, dispatch, retries, and network policy. Add a focused handler test;
do not edit the worker or dispatcher for each crawler.

Infrastructure is grouped by responsibility: contracts and models in `domain/`,
submission in `application/`, database access in `persistence/`, Hatchet execution
in `runtime/`, and outbound HTTP policy in `network/`.

## Task input

Hatchet receives identifiers and routing metadata only:

```python
class CrawlTaskInput(BaseModel):
    crawl_job_id: UUID
    tenant_id: UUID
    target_url_id: UUID
    target_host: str
```

Do not pass HTML, credentials, cookies, proxy secrets, or large payloads.
Workers load tenant-scoped state by ID and persist progress idempotently.

## Defaults and failure policy

- Each `target_host` gets at most two concurrent tasks and one task per second.
- A task runs at most three times, with exponential backoff capped at five
  minutes and a five-minute execution timeout.
- Network failures, timeouts, HTTP 408/429, and 5xx responses are retryable.
  Other 4xx responses, validation failures, and policy failures are terminal.
- Raw response bodies are never persisted. The safe HTTP client blocks private
  and special-use addresses, pins the validated destination IP, and revalidates
  redirect hops.
- Browser automation belongs on a dedicated worker when a real handler needs it.

See Hatchet's official guidance for [concurrency](https://docs.hatchet.run/v1/concurrency),
[rate limits](https://docs.hatchet.run/v1/rate-limits),
[idempotency](https://docs.hatchet.run/v1/idempotency), and
[retry policies](https://docs.hatchet.run/v1/retry-policies).
