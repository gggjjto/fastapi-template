# Engineering Foundation Design

## Related Documents

- `docs/fastapi-saas-infrastructure-architecture-blueprint.md` — high-level SaaS infrastructure and application architecture blueprint.
- `docs/engineering-foundation-requirements.md` — requirements, priorities, and acceptance criteria.

## 1. Overview

This document describes the technical design for upgrading the FastAPI template's engineering foundation. It is intended to be executable by future AI agents in small phases.

The project should remain a modular monolith organized by domain:

```text
app/
  auth/
  users/
  health/
  core/
  db/
```

Cross-cutting infrastructure belongs in `app/core`, authentication and authorization belong in `app/auth`, persistence concerns remain in `app/db`, and business-specific code remains in each domain.

## 2. Architecture Principles

- Keep routers thin. Routers adapt HTTP to application use cases.
- Keep business rules in services.
- Keep database access in repositories.
- Keep cross-cutting behavior centralized.
- Prefer explicit dependencies over hidden global state.
- Prefer stable codes and structured metadata over parsing message strings.
- Preserve backwards compatibility only for public API contracts that have been documented.

## 3. Proposed Module Layout

New or changed modules:

```text
app/
  core/
    response.py          # ApiResponse envelope
    error_codes.py       # common error codes
    exceptions.py        # DomainError hierarchy
    error_handlers.py    # global exception handlers
    request_context.py   # request_id/user_id/tenant_id context helpers
    i18n.py              # locale negotiation and message lookup
    logging.py           # structlog setup and redaction processors
    middleware.py        # request ID and access log middleware
    openapi.py           # reusable OpenAPI response helpers
  auth/
    constants.py         # auth error codes and permission constants
    models.py            # auth session, role, permission models
    repository.py        # auth session and RBAC queries
    service.py           # login, refresh, logout, permission resolution
    dependencies.py      # CurrentUser, RequirePermission, RequireRole
    security.py          # token encode/decode/hash helpers
  users/
    constants.py         # user error codes and permissions
```

Alembic:

```text
alembic/
  versions/
    <timestamp>_initial_schema.py
```

Documentation:

```text
docs/
  engineering-foundation-requirements.md
  engineering-foundation-design.md
```

## 4. API Response Design

### 4.1 Response Shape

Target shape:

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "req_..."
}
```

For errors:

```json
{
  "code": "USER_NOT_FOUND",
  "message": "用户不存在",
  "data": null,
  "request_id": "req_..."
}
```

### 4.2 Compatibility Note

Current `ApiResponse.code` is an integer HTTP-like code. The recommended end state is a string business code. To reduce breakage, implement this in one of two ways:

Option A, direct change:

- Change `code` to `str`.
- Use `"OK"` for success.
- Update all tests and docs.

Option B, transitional shape:

```json
{
  "code": 200,
  "error_code": "USER_NOT_FOUND",
  "message": "用户不存在",
  "data": null,
  "request_id": "req_..."
}
```

Recommendation: choose Option A if the project has no external API consumers yet. Choose Option B if clients already depend on numeric `code`.

### 4.3 Implementation

File: `app/core/response.py`

Responsibilities:

- Define `ApiResponse[T]`.
- Provide `ok(data, message="success")`.
- Provide `error(code, message, data=None)`.
- Include optional `request_id`.

Request ID should be filled by exception handlers and optionally by a helper for successful responses if the request object is available.

## 5. Error Code Design

### 5.1 Common Codes

File: `app/core/error_codes.py`

Suggested constants:

```python
class CommonErrorCode:
    OK = "OK"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
```

### 5.2 Domain Codes

Auth:

```python
class AuthErrorCode:
    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    SESSION_REVOKED = "AUTH_SESSION_REVOKED"
    PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"
```

Users:

```python
class UserErrorCode:
    NOT_FOUND = "USER_NOT_FOUND"
    EMAIL_CONFLICT = "USER_EMAIL_CONFLICT"
    INACTIVE = "USER_INACTIVE"
```

### 5.3 Rules

- Error codes are stable API contract.
- Error code strings must not be translated.
- Error code names should include the domain prefix.
- Error messages can change and can be localized.

## 6. Exception Design

### 6.1 Base Exception

File: `app/core/exceptions.py`

Target structure:

```python
class DomainError(Exception):
    code: str
    message: str
    status_code: int
    message_key: str | None
    params: dict[str, object]
```

Constructor behavior:

- Accept `code`, `message`, `status_code`, optional `message_key`, and optional `params`.
- `message` is the fallback message.
- `message_key` is used by i18n.
- `params` are interpolation values for translated messages.

Recommended subclasses:

```text
BadRequestError
UnauthorizedError
ForbiddenError
NotFoundError
ConflictError
ValidationDomainError
```

### 6.2 Domain Exceptions

Example:

```python
class UserNotFound(NotFoundError):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(
            code=UserErrorCode.NOT_FOUND,
            message="User not found",
            message_key="errors.user.not_found",
            params={"user_id": str(user_id)},
        )
```

### 6.3 Handler Flow

File: `app/core/error_handlers.py`

Handlers:

- `DomainError` -> response with `exc.status_code`.
- `HTTPException` -> response with mapped common code.
- `RequestValidationError` -> `VALIDATION_ERROR`.
- `RateLimitExceeded` -> `RATE_LIMITED`.
- `Exception` -> log exception and return `INTERNAL_SERVER_ERROR`.

Important:

- Unexpected exceptions must not leak stack traces.
- Domain errors should log at warning level for 4xx and error level for 5xx.
- Include `request_id`, `path`, `method`, and `error_code` in logs.

## 7. Logging Design

### 7.1 Request Context

File: `app/core/request_context.py`

Use `contextvars` to store:

```text
request_id
user_id
tenant_id
```

Existing `RequestIDMiddleware` should bind `request_id` into structlog context.

### 7.2 Access Logs

Extend middleware to log one event per request:

```text
event="http.request"
method
path
status_code
duration_ms
request_id
client_ip
```

If available:

```text
user_id
tenant_id
```

### 7.3 Redaction

Add a logging processor to redact sensitive keys:

```text
password
token
access_token
refresh_token
authorization
cookie
secret
```

### 7.4 Testing

Tests should verify:

- `X-Request-ID` header exists.
- Provided `X-Request-ID` is propagated.
- Error logs include error code where practical.

## 8. Configuration Design

File: `app/core/config.py`

### 8.1 Settings Model

Continue using:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")
```

Add environment helpers:

```python
@property
def is_production(self) -> bool: ...

@property
def is_test(self) -> bool: ...
```

### 8.2 Production Validation

Add a model validator that runs after settings are loaded.

Rules:

- Reject default JWT secret in production.
- Reject wildcard CORS origins in production.
- Reject `db_create_tables_on_startup=true` in production.
- Reject non-PostgreSQL database URL in production.
- Require JSON logs in production or document why not.

### 8.3 Environment Files

Suggested docs convention:

```text
.env.example       # documented defaults
.env               # local only, gitignored
```

Do not add committed `.env.production`.

## 9. Database Migration Design

The project uses SQLAlchemy, so migration must use Alembic.

### 9.1 Initial Migration

Add the first migration under `alembic/versions/` for the current schema.

The migration should include current application tables, at minimum:

- `users`

When RBAC and sessions are implemented, add migrations for:

- `auth_sessions`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`

### 9.2 Migration Rules

- Never use `create_all` in production.
- Every model change requires a migration.
- Prefer forward-compatible migrations.
- For risky changes, use expand-contract:
  1. Expand schema.
  2. Backfill.
  3. Switch application code.
  4. Contract old schema.

### 9.3 CI

Keep CI checks:

- `alembic upgrade head`
- `alembic downgrade base` where supported

Consider adding:

- Check for model/migration drift.

## 10. JWT Authentication Design

### 10.1 Token Types

Access token:

- Short-lived.
- Contains `sub`, `type=access`, `exp`, and optionally `jti`.

Refresh token:

- Long-lived.
- Contains `sub`, `type=refresh`, `exp`, `jti`, and `session_id`.
- Server-side session record must exist and not be revoked.

### 10.2 Session Model

File: `app/auth/models.py`

Suggested table: `auth_sessions`

Fields:

```text
id: UUID primary key
user_id: UUID foreign key users.id
refresh_token_hash: str
user_agent: str | null
ip_address: str | null
expires_at: datetime
revoked_at: datetime | null
created_at: datetime
updated_at: datetime
```

Optional later fields:

```text
last_used_at
rotated_at
replaced_by_session_id
```

### 10.3 Refresh Rotation Flow

1. Client sends refresh token.
2. Decode token and read `session_id`.
3. Load session.
4. Verify session is active.
5. Compare token hash.
6. Revoke or rotate the old token hash.
7. Issue new access token and new refresh token.
8. Store hash of new refresh token.

### 10.4 Logout Flow

Logout endpoint:

```text
POST /api/v1/auth/logout
```

Behavior:

- Requires refresh token or current session identifier.
- Marks session as revoked.
- Returns success even if already revoked, if this does not weaken security.

### 10.5 Tests

Cover:

- Login creates session.
- Refresh rotates token.
- Old refresh token fails after rotation.
- Logout revokes session.
- Revoked session cannot refresh.

## 11. RBAC Design

### 11.1 Initial Model

File: `app/auth/models.py`

Tables:

```text
roles
permissions
user_roles
role_permissions
```

Suggested fields:

```text
roles:
  id
  name
  description
  created_at

permissions:
  id
  code
  description
  created_at

user_roles:
  user_id
  role_id

role_permissions:
  role_id
  permission_id
```

Unique constraints:

- `roles.name`
- `permissions.code`
- `(user_roles.user_id, user_roles.role_id)`
- `(role_permissions.role_id, role_permissions.permission_id)`

### 11.2 Permission Naming

Format:

```text
resource:action
```

Initial permissions:

```text
users:read
users:create
users:update
users:delete
roles:read
roles:manage
```

### 11.3 Dependencies

File: `app/auth/dependencies.py`

Add:

```python
class RequirePermission:
    def __init__(self, permission: str) -> None: ...
    async def __call__(self, current_user: CurrentUser, session: DBSession) -> None: ...
```

Behavior:

- If user is not authenticated, return 401.
- If user lacks permission, raise `ForbiddenError`.
- Cache permissions per request where practical.

### 11.4 Route Usage

Example:

```python
@router.get(
    "",
    dependencies=[Depends(RequirePermission("users:read"))],
)
async def list_users(...):
    ...
```

### 11.5 Future Tenant Scope

When SaaS tenancy is added:

- Replace `user_roles` with organization-scoped membership roles.
- Add `organization_members`.
- Resolve permissions in the context of `tenant_id`.

Do not block the initial RBAC implementation on full tenancy.

## 12. Internationalization Design

### 12.1 Scope

Start with error messages only.

Supported locales:

```text
zh-CN
en-US
```

### 12.2 Message Files

Suggested layout:

```text
locales/
  zh-CN.json
  en-US.json
```

Example:

```json
{
  "errors.user.not_found": "用户不存在",
  "errors.auth.invalid_token": "无效的登录凭证"
}
```

### 12.3 Locale Resolution

File: `app/core/i18n.py`

Resolution order:

1. Explicit user preference, when available.
2. `Accept-Language` header.
3. Default locale from settings.

### 12.4 Handler Integration

`DomainError` carries:

```text
message_key
params
```

The global exception handler translates the message before returning the response.

### 12.5 Fallback

If translation is missing:

- Use default locale.
- If still missing, use `DomainError.message`.

## 13. OpenAPI Documentation Design

### 13.1 Route Requirements

Every route should include:

```text
summary
description
response_model
responses
tags
```

For protected routes:

- Ensure bearer auth is visible in OpenAPI.

### 13.2 Shared Helpers

File: `app/core/openapi.py`

Provide helpers:

```python
def error_responses(*codes: int) -> dict[int, dict[str, object]]:
    ...
```

Common responses:

```text
400 BAD_REQUEST
401 UNAUTHORIZED
403 FORBIDDEN
404 NOT_FOUND
409 CONFLICT
422 VALIDATION_ERROR
429 RATE_LIMITED
500 INTERNAL_SERVER_ERROR
```

### 13.3 Examples

Public and important endpoints should include examples for:

- Success response.
- Validation error.
- Authentication error.
- Permission error.

### 13.4 OpenAPI in Production

Current behavior hides OpenAPI outside development and test. Keep this default.

If production docs are required later:

- Put docs behind authentication or internal network access.
- Do not make public docs the default.

## 14. Implementation Plan

### Phase 1: Error Contract

Files:

- `app/core/response.py`
- `app/core/error_codes.py`
- `app/core/exceptions.py`
- `app/core/error_handlers.py`
- `app/auth/exceptions.py`
- `app/users/exceptions.py`
- tests under `tests/core/`, `tests/auth/`, `tests/users/`

Steps:

1. Add common error codes.
2. Enhance `DomainError`.
3. Add global `DomainError` handler.
4. Refactor domain exceptions to include codes.
5. Remove router-level domain exception translation where appropriate.
6. Update tests.

### Phase 2: Config and Migration

Files:

- `app/core/config.py`
- `alembic/versions/<initial>.py`
- README or docs
- tests under `tests/core/`

Steps:

1. Add production settings validator.
2. Add tests for unsafe production config.
3. Generate initial Alembic migration.
4. Verify migration upgrade/downgrade.
5. Update docs.

### Phase 3: JWT Sessions

Files:

- `app/auth/models.py`
- `app/auth/repository.py`
- `app/auth/service.py`
- `app/auth/security.py`
- `app/auth/router.py`
- Alembic migration
- tests under `tests/auth/`

Steps:

1. Add `auth_sessions` model.
2. Add token hash helpers.
3. Update login to create session.
4. Update refresh to rotate token.
5. Add logout endpoint.
6. Add tests.

### Phase 4: RBAC

Files:

- `app/auth/models.py`
- `app/auth/repository.py`
- `app/auth/service.py`
- `app/auth/dependencies.py`
- `app/auth/constants.py`
- `app/users/router.py`
- Alembic migration
- tests under `tests/auth/` and `tests/users/`

Steps:

1. Add role and permission models.
2. Add permission query methods.
3. Add `RequirePermission`.
4. Protect user list/detail endpoints.
5. Add tests for 401, 403, and allowed access.

### Phase 5: i18n and OpenAPI

Files:

- `app/core/i18n.py`
- `app/core/openapi.py`
- `locales/zh-CN.json`
- `locales/en-US.json`
- domain routers
- tests under `tests/core/`

Steps:

1. Add locale negotiation.
2. Add translation catalog.
3. Integrate translation into error handlers.
4. Add OpenAPI error response helpers.
5. Update route metadata.
6. Add tests.

### Phase 6: Logging Hardening

Files:

- `app/core/logging.py`
- `app/core/middleware.py`
- `app/core/request_context.py`
- tests under `tests/core/`

Steps:

1. Add request context helpers.
2. Add access logs.
3. Add redaction processor.
4. Ensure exception handlers bind error metadata.
5. Add tests where practical.

## 15. Test Strategy

Run locally:

```bash
make test-up
make ci
```

Targeted test examples:

```bash
uv run pytest tests/core/test_middleware.py -v
uv run pytest tests/core/test_error_handlers.py -v
uv run pytest tests/auth/test_auth.py -v
uv run pytest tests/users/test_users.py -v
```

Coverage expectations:

- Error handlers cover expected error shapes.
- Auth tests cover login, refresh, logout, revoked session.
- RBAC tests cover no token, no permission, and success.
- Config tests cover unsafe production settings.
- i18n tests cover locale and fallback behavior.

## 16. Rollout Guidance

Recommended PR order:

1. Error contract and global exception handling.
2. Initial Alembic migration and production config validation.
3. JWT session and logout.
4. RBAC models and permission dependency.
5. i18n error messages.
6. OpenAPI route documentation cleanup.
7. Logging and redaction hardening.

Each PR should:

- Be independently testable.
- Include migration if it changes models.
- Update docs if behavior or setup changes.
- Avoid unrelated refactors.

## 17. Risks and Mitigations

Risk: Changing `ApiResponse.code` from integer to string may break clients.

Mitigation: Use the transitional shape with `error_code`, or confirm no external clients exist before changing.

Risk: RBAC can become over-engineered.

Mitigation: Start with simple global roles and permissions. Defer tenant-scoped RBAC until tenant models exist.

Risk: Refresh token rotation can lock users out if implemented incorrectly.

Mitigation: Add focused tests for rotation, reuse, logout, and expiration before broad rollout.

Risk: i18n can spread message lookup across business code.

Mitigation: Keep translation in exception handlers. Business code raises coded exceptions with message keys.

Risk: Initial migration may diverge from models.

Mitigation: Generate from metadata, inspect manually, and verify with clean database upgrade.

## 18. Definition of Done

The initiative is complete when:

- All P0 requirements in the requirements document are implemented.
- Existing tests pass.
- New tests cover the changed cross-cutting behavior.
- Alembic migration baseline exists.
- User APIs have explicit auth and permission rules.
- Known errors have stable error codes.
- Production settings fail fast on unsafe defaults.
- OpenAPI docs follow the standard for existing routes.
- README or docs explain the new conventions.
