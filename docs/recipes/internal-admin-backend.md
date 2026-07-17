# Internal Admin Backend

Use this recipe for operations tools, dashboards, internal APIs, and admin
workflows.

Keep:

- `app/auth` and RBAC if different internal roles need different permissions
- `app/users` as an operator/account pattern
- Structured logs and request IDs for auditability

Consider removing:

- Public signup flows if all users are provisioned internally
- i18n catalogs if the tool is single-language

Add next:

- Admin-specific domains
- Audit log models
- Read-heavy list endpoints with pagination and filters

Verify:

```bash
make api-test-up
make api-ci
```
