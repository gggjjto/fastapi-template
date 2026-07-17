# AI-enabled API

Use this recipe when an API needs LLM calls, agent workflows, prompt templates,
or async AI jobs.

Keep:

- `app/core`
- `app/db`
- `app/worker.py` for slow or retryable AI work
- Auth and RBAC for user-owned conversations or files

Add next:

- `app/ai` for provider adapters and model configuration
- `app/conversations` for message and run history
- `app/files` for uploads, parsing, and retrieval inputs
- Prompt templates in a clearly versioned location

Provider guidance:

- Store API keys in environment variables.
- Keep provider-specific code behind a small internal interface.
- Record model name, provider, latency, token usage, and request ID for each run.

Verify:

```bash
make api-test-up
make api-ci
```
