# Shared Config

Shared JavaScript and TypeScript configuration for workspace apps.

## Exports

- `@rapid-template/config/tsconfig/base.json` - strict TypeScript defaults.
- `@rapid-template/config/tsconfig/next.json` - Next.js App Router TypeScript defaults.
- `@rapid-template/config/eslint/ignores` - shared ESLint ignore patterns for Next.js apps.

Keep this package configuration-only. Add runtime helpers to a dedicated package
once at least one app needs them.
