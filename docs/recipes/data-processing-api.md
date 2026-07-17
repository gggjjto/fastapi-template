# Data Processing API

Use this recipe for ingestion, transformation, enrichment, report generation,
and scheduled data workflows.

Keep:

- PostgreSQL and SQLAlchemy for durable state
- Redis and Arq for queued processing
- Structured logging and request IDs
- Sentry for production error visibility

Add next:

- Input validation schemas for uploaded or submitted data
- Job status and result models
- File/object-storage integration if inputs or outputs are large
- Metrics for processed records, failures, retries, and latency

Verify:

```bash
make api-test-up
make api-ci
```
