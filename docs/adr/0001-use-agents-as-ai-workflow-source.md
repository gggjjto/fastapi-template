# ADR-0001: Use `.agents` as the AI Workflow Source

## Status

Accepted

## Date

2026-06-05

## Context

This repository is intended to support AI-assisted development across multiple
coding agents. It previously had overlapping AI instructions under `.claude`,
`.codex`, `.agents`, `CLAUDE.md`, and `AGENTS.md`.

That split created avoidable drift:

- Skills referenced paths such as `.Codex/rules/...` that did not exist.
- Claude-specific files duplicated the same project rules later needed by other
  agents.
- Community skills from `npx skills` use the `SKILL.md` format and can install
  cleanly into `.agents/skills/`.
- Future agents need one obvious place to read workflows, rules, and active
  requirements.

## Decision

Use `.agents` as the single source of truth for AI development workflows:

- `.agents/skills/` stores local project workflows and installed community
  skills.
- `.agents/rules/` stores reusable project rules.
- `.agents/requirements.md` stores active requirements and decision context.
- `AGENTS.md` is the root entry point that points agents to `.agents`.
- Community skills are managed with `npx skills` and recorded in
  `skills-lock.json`.

Project-level community skills must be installed with:

```bash
npx skills add <owner/repo> --skill <skill-name> --agent codex --copy -y
```

Do not use `--agent "*"`, because it creates many tool-specific directories.

## Alternatives Considered

### Keep `.claude` as the Source of Truth

- Pros: Existing files were already tracked and familiar from earlier work.
- Cons: Claude-specific naming is misleading for a multi-agent workflow and
  duplicates `.agents` community conventions.

### Keep `.codex` as the Source of Truth

- Pros: Matches the current coding agent used in this workspace.
- Cons: Codex-specific naming repeats the same lock-in problem and is not the
  default community skill location.

### Keep All Tool-Specific Directories

- Pros: Each tool can read its native files.
- Cons: Rules drift quickly, path references become fragile, and future agents
  cannot know which copy is authoritative.

## Consequences

### Positive

- One canonical location for AI rules and requirements.
- `npx skills list --json` can identify installed project skills from
  `.agents/skills`.
- Community skills and local workflows use the same `SKILL.md` shape.
- Documentation now points to `AGENTS.md` and `.agents`.

### Negative

- Tool-specific files such as `.claude` and `CLAUDE.md` are removed.
- If a future tool requires a native directory, it must be generated as a thin
  compatibility layer that points back to `.agents`.

### Follow-up

- Keep `skills-lock.json` reviewed with changes to community skills.
- Write new ADRs for future expensive-to-reverse workflow or architecture
  decisions.

## References

- [.agents/README.md](../../.agents/README.md)
- [.agents/requirements.md](../../.agents/requirements.md)
- [skills-lock.json](../../skills-lock.json)
