---
doc_type: adr
status: active
authority: supporting
scope: documentation-system
last_reviewed: 2026-08-12
---

# ADR-0002: Govern Documentation as a Knowledge System

## Status

Accepted

## Date

2026-08-12

## Context

Earlier documentation mixed current state, target architecture, completed requirements, recipes, and implementation plans. Humans could read the prose, but agents could not reliably decide whether a claim was current, normative, proposed, or historical. Stale documents described missing features that already existed.

## Decision Drivers

- Humans and agents must use the same knowledge layer.
- Executable facts and desired state must remain distinguishable.
- Discovery, authority, lifecycle, and conflict handling must be machine-checkable.
- The solution must stay inside Markdown and the existing repository Harness.

## Decision

Treat `docs/` as a typed, governed knowledge system:

1. `docs/README.md` routes questions to their authority.
2. Every Markdown document declares type, status, authority, scope, and review date.
3. Code, tests, migrations, and configuration remain the source for current behavior.
4. `AGENTS.md` and `.agents/` own agent execution and active intent.
5. ADRs own durable rationale; conventions own stable boundaries; runbooks own operations.
6. The deterministic Harness rejects missing metadata, invalid authority/lifecycle combinations, unindexed files, and broken links.

The previous broad blueprints, completed requirement/design documents, and speculative recipes are removed rather than archived in the active tree; Git history remains the archive.

## Alternatives Considered

### Keep the old documents and add an index

Rejected because discovery alone does not prevent stale prose from acting as current truth.

### Add a documentation platform or semantic search

Rejected because those tools improve retrieval, not authority. Markdown plus deterministic checks covers the present failure mode without a new dependency.

## Consequences

### Positive

- Agents can select context before reading deeply.
- The active documentation set is small and evidence-based.
- Structural drift fails locally and in CI.

### Negative

- Every document carries a small metadata header.
- The catalog must change with the docs tree.
- Semantic accuracy still requires review alongside code changes.

## References

- [Documentation entry](../README.md)
- [Harness Engineering](../harness-engineering.md)
- [Documentation maintenance rule](../../.agents/rules/docs-maintenance.md)
