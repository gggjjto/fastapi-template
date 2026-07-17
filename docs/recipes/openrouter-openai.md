# OpenRouter / OpenAI

Use this recipe when an API needs to call hosted LLM providers while keeping
provider keys and request shaping out of route handlers.

## Setup

```bash
make create-project name=ai-api target=../ai-api
cd ../ai-api
make api-install
cp apps/api/.env.example apps/api/.env
```

Add provider settings to `apps/api/.env`.

## Env Vars

```bash
OPENAI_API_KEY=
OPENROUTER_API_KEY=
APP_AI_PROVIDER=openai
APP_AI_MODEL=gpt-4.1-mini
```

Use one provider key at a time until the service layer has explicit fallback
logic.

## Implementation Notes

- Add an `app/ai/` domain with `schemas.py`, `service.py`, `router.py`, and
  tests.
- Keep provider SDK calls in `app/ai/service.py`; routers should only validate
  input and return the standard API response envelope.
- Store prompts and model defaults in code or config, not in route handlers.
- Redact provider keys and prompt payloads in logs when they may contain user
  data.
- If streaming is needed, add it as a separate endpoint so non-streaming calls
  stay easy to test.

## Verification

```bash
make api-lint
make api-format-check
make api-typecheck
make api-test
```

For live-provider smoke tests, use a separate opt-in test file and require the
matching provider key in the environment.
