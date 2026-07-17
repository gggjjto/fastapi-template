# Web App

Next.js App Router workspace for the rapid development template.

## Commands

Run from the repository root:

```bash
pnpm install
make web-dev
make web-lint
make web-typecheck
make web-build
```

Or run directly in this package:

```bash
pnpm --filter @rapid-template/web dev
pnpm --filter @rapid-template/web lint
pnpm --filter @rapid-template/web typecheck
pnpm --filter @rapid-template/web build
```

The development server runs at `http://localhost:3000`.

## Notes

- Keep this app usable without the API running; API-backed features should show
  explicit loading and error states.
- Prefer shared packages only when at least one app imports them.
- Use root Turbo commands for workspace-wide validation.
