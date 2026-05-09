---
description: Documentation maintenance rules for this FastAPI template
---

## Documentation step

Every feature, behavior change, workflow change, or public contract change must include a documentation check before finishing.

Use this order:

1. Identify what changed from a user or maintainer point of view.
2. Decide whether documentation must change.
3. Update the smallest relevant document.
4. If no document change is needed, mention why in the final response.

## What to update

- `README.md`: setup, features, API examples, config, Docker, CI/CD, troubleshooting.
- `CLAUDE.md`: repository-wide agent instructions, commands, architecture, conventions.
- `.claude/rules/*.md`: reusable AI coding rules and project-specific workflows.
- `CONTRIBUTING.md`: local checks, PR process, review expectations.
- `SECURITY.md`: vulnerability reporting, supported versions, security expectations.
- `.github/pull_request_template.md`: PR self-checks that should happen every time.

## Triggers

Update docs when changing:

- Public API routes, request/response schemas, status codes, or auth requirements.
- Environment variables, defaults, startup behavior, or deployment assumptions.
- Test commands, CI jobs, Makefile targets, Docker/compose files, or release workflow.
- Domain scaffolding conventions, layer responsibilities, or AI development workflow.
- Security posture such as JWT, CORS, rate limits, OpenAPI visibility, or secret handling.

## Boundaries

- Keep docs concise and factual; do not duplicate long content across files.
- Prefer linking to the source file over copying implementation details.
- Do not document speculative features as already implemented.
- Do not update changelogs unless the user asks for release notes or changelog output.
