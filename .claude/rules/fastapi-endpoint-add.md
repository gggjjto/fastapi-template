---
description: Rules for adding or changing API endpoints in this FastAPI template
paths:
  - "app/**/*.py"
---

## Endpoint implementation checklist

Before editing, identify:

- Route path and method.
- Required auth guard (`CurrentUser`) or public access.
- Request schema, response schema, and validation constraints.
- Domain errors and their HTTP status mapping.
- Repository queries needed by the service.

## Router rules

- Keep handlers small and readable.
- Include `summary`, `description`, and `response_model` on every route decorator.
- Use `responses=` for expected non-200 outcomes such as 400, 401, 403, 404, 409, and 422.
- Return `ApiResponse.ok(data)` for success.
- Catch domain exceptions at the router boundary and convert them to HTTP responses.

## Service and repository rules

- Services own business decisions and transaction-level behavior.
- Repositories own database reads/writes and should not import FastAPI.
- Do not leak SQLAlchemy models as public response schemas unless the existing domain already does so.
- Use explicit cross-domain imports, e.g. `from app.auth import constants as auth_constants`.

## Safety defaults

- Public endpoints must be intentional. If the endpoint reads user or tenant data, default to requiring `CurrentUser`.
- Add rate limiting with `@limiter.limit(...)` for auth-like, write-heavy, or abuse-prone endpoints.
- Do not broaden CORS, expose docs in production, or weaken JWT settings as part of endpoint work.
