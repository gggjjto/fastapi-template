---
doc_type: adr
status: active
authority: supporting
scope: agent-workflow
last_reviewed: 2026-08-12
---

# ADR-0001: Use `.agents` as the AI Workflow Source

## Status

Accepted

## Date

2026-06-05

## Context

The repository is used by multiple coding agents. Tool-specific rule directories create duplicate instructions, path drift, and uncertainty about which copy is authoritative.

## Decision

Use `.agents/` as the repository-local source of truth for AI development workflows:

- `.agents/skills/` stores workflows;
- `.agents/rules/` stores reusable execution rules;
- `.agents/requirements.md` stores active requirements;
- `AGENTS.md` remains the short repository entry point.

Community skills are installed with `--agent codex --copy -y` so `skills-lock.json` records them without creating parallel tool directories.

## Alternatives Considered

### Tool-specific directories

Rejected because every additional copy can drift and makes multi-agent behavior depend on the selected tool.

### Put everything in `AGENTS.md`

Rejected because one large always-loaded file mixes routing, detailed workflows, requirements, and project conventions.

## Consequences

### Positive

- One portable workflow source across agents.
- Rules, requirements, and executable skills have separate lifecycles.
- Deterministic checks can reject forbidden parallel sources.

### Negative

- Tools requiring native files need a thin compatibility pointer.
- Installed skills must be reviewed and tracked deliberately.

## References

- [Agent workflow index](../../.agents/README.md)
- [Active requirements](../../.agents/requirements.md)
- [Harness Engineering](../harness-engineering.md)
