# Security Review

Use this workflow before shipping auth, user data, config, CI, or externally visible API changes.

## Workflow

1. Use `security-reviewer` to review the changed surface.
2. Check endpoint exposure:
   - Is public access intentional?
   - Should `CurrentUser` or a narrower guard be required?
3. Check JWT, CORS, OpenAPI visibility, rate limits, and secret handling.
4. Check input validation and documented error responses.
5. Check CI/security scan changes do not weaken gates.
6. Add or request tests for security-relevant behavior.
7. Run docs maintenance check when security posture changes.

## Common risks

- Public user, tenant, billing, or admin reads.
- Missing 401/403/404/409/422 responses in route docs.
- Weak production JWT secret defaults.
- Broad CORS in non-development environments.
- OpenAPI exposed in production by accident.
- Rate limits missing on auth-like or abuse-prone endpoints.

## Output

Return findings first:

1. Critical/high/medium/low issue list.
2. File paths and concrete risk.
3. Missing tests or docs.
4. Residual risk if no issues are found.
