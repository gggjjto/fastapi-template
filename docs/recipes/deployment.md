# Deployment

Use this recipe to prepare a generated project for a production-like deployment
with separate API, worker, database, Redis, and optional web hosting.

## Setup

```bash
make create-project name=deployable-api target=../deployable-api
cd ../deployable-api
make api-install
cp apps/api/.env.example apps/api/.env
make api-ci
make api-docker-build
```

Choose the hosting target before adding provider-specific files. Keep the API
Docker image as the portable baseline.

## Env Vars

```bash
APP_ENV=production
APP_DATABASE_URL=
APP_REDIS_URL=
APP_JWT_SECRET=
APP_CORS_ORIGINS=
APP_SENTRY_DSN=
```

Set secrets in the deployment platform, not in repository files.

## Implementation Notes

- Deploy the API and worker as separate processes from the same image.
- Run Alembic migrations as an explicit release step before shifting traffic.
- Configure health checks against `/health` or a deployment-specific readiness
  endpoint.
- Use managed PostgreSQL and Redis for production unless a platform constraint
  requires self-hosting.
- Keep frontend deployment independent from the API deployment when using a web
  workspace.
- Add rollback notes for database migrations that cannot be safely downgraded.

## Verification

```bash
make api-ci
make api-docker-build
docker run --rm \
  -e APP_ENV=test \
  -e APP_JWT_SECRET=ci-smoke \
  -e APP_DATABASE_URL="sqlite+aiosqlite:///./smoke.db" \
  -e APP_DB_CREATE_TABLES_ON_STARTUP=true \
  deployable-api:local python -c "from app.main import app; print(app.title)"
```

After deployment, verify migrations, health checks, login, a protected endpoint,
worker startup, and error tracking delivery if Sentry is enabled.
