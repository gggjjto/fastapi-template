# Admin App

Next.js App Router administration console for Rapid Development Template.

The browser authenticates through Route Handlers. Access and refresh tokens stay
in HttpOnly cookies; admin pages call the FastAPI service through `/api/backend/*`.

Set `API_BASE_URL` for the server-side FastAPI origin. It defaults to
`http://127.0.0.1:8000` for local development.

## Commands

Run from the repository root:

```bash
pnpm install
make admin-dev
make admin-lint
make admin-typecheck
make admin-build
```

Or run directly in this package:

```bash
pnpm --filter @rapid-template/admin dev
pnpm --filter @rapid-template/admin lint
pnpm --filter @rapid-template/admin typecheck
pnpm --filter @rapid-template/admin build
```

The development server runs at `http://localhost:3001`.

## Notes

- Keep this app usable without the API running; API-backed features should show
  explicit loading and error states.
- Prefer shared packages only when at least one app imports them.
- Use root Turbo commands for workspace-wide validation.
