# FastAPI API Template Options

The `fastapi-api` template currently includes the production-minded backend
surface by default. The `--with-*` flags record requested capabilities and
validate combinations before future slimmer variants start removing files.

## Flags

| Flag | Status | Files affected | Env vars affected | Notes |
| --- | --- | --- | --- | --- |
| `--with-auth` | Included by default | `apps/api/app/auth`, `apps/api/tests/auth`, `apps/api/app/core/config.py` | `APP_JWT_SECRET`, `APP_ACCESS_TOKEN_EXPIRE_MINUTES`, `APP_REFRESH_TOKEN_EXPIRE_DAYS` | JWT access and refresh-token authentication endpoints. |
| `--with-rbac` | Included by default | `apps/api/app/auth/models.py`, `apps/api/app/auth/repository.py`, `apps/api/app/auth/seed.py`, `apps/api/tests/auth/test_seed.py` | None | Requires `--with-auth`. |
| `--with-redis` | Included by default | `apps/api/app/db/redis.py`, `apps/api/app/core/cache.py`, `apps/api/docker-compose.yml`, `apps/api/docker-compose.test.yml` | `APP_REDIS_URL` | Enables Redis lifecycle and cache helpers. |
| `--with-worker` | Included by default | `apps/api/app/worker.py`, `apps/api/app/crawler`, `apps/api/tests/crawler`, `apps/api/tests/core/test_tasks.py` | `HATCHET_CLIENT_TOKEN` | Uses Hatchet Cloud; the API stays token-free while worker and crawler dispatcher use the token. |
| `--with-sentry` | Included by default | `apps/api/app/core/sentry.py`, `apps/api/app/main.py`, `apps/api/app/core/config.py` | `APP_SENTRY_DSN`, `APP_SENTRY_TRACES_SAMPLE_RATE` | Empty DSN keeps Sentry disabled at runtime. |
| `--with-ai` | Metadata only | `docs/recipes` | `OPENAI_API_KEY`, `OPENROUTER_API_KEY` | No AI runtime files are generated yet. |

## Valid Combinations

```bash
python3 scripts/create_project.py my-api ../my-api --with-auth --with-rbac
python3 scripts/create_project.py jobs-api ../jobs-api --with-worker
python3 scripts/create_project.py ai-api ../ai-api --with-ai
```

Invalid combinations fail before files are copied:

```bash
python3 scripts/create_project.py bad-api ../bad-api --with-rbac
```
