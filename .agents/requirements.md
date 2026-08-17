# Requirements Log

Track **active** requirements only. Git history is the archive — do not keep superseded or implemented entries here.

## Lifecycle rules

- **Add** an entry when a requirement is proposed or changed during a conversation.
- **Remove** an entry when the requirement is fully implemented and merged, or abandoned.
- **Split** into `.agents/requirements/<domain>.md` when any domain exceeds ~5 active entries; update this file to link to it.
- **Compress** multiple evolving entries for the same requirement into one "current state" entry.
- For detailed process notes per domain, see `.agents/requirements/INDEX.md` and referenced files.

## Format

```
### [Domain / Feature] — YYYY-MM-DD
**Requirement:** what was decided
**Change from:** (if modifying a prior requirement) what it replaced
**Reason:** why the change was made
```

---

<!-- Active requirements below -->

### Requirements Governance — 2026-06-10
**Requirement:** Keep a scalable requirement governance process when requirements shift during development: update `.agents/requirements.md` immediately, remove outdated behavior instead of adding compatibility shims, and store detailed change governance under `.agents/requirements/` with a lightweight index.
**Change from:** Replaces ad-hoc requirement notes and makes mid-implementation changes explicit and traceable.
**Reason:** This project already sees requirement churn; a stable process reduces drift between PR discussion, code, and tests.
**Decisions:**
- Add `.agents/requirements/agent-workflow.md` as the operational workflow for requirement changes.
- Add `.agents/rules/requirements-governance.md` as the execution rule for agents.
- Add `.agents/rules/INDEX.md` and `.agents/requirements/INDEX.md` for discoverability.
**Status:** Accepted and active.
