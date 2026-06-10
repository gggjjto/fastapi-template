---
description: Requirement governance and mid-flight change handling for AI-assisted work
---

# Requirements Governance

## Why requirement governance exists

Requirements often change after implementation review. This rule prevents
silent fallback logic and makes every change traceable.

## Source of truth layers

1. `docs/adr/*.md` for long-lived architectural decisions.
2. `.agents/requirements.md` for active short-form requirements.
3. `.agents/requirements/*.md` for domain-level operational details.
4. `.agents/rules/*.md` for working conventions.

## Mandatory update flow for requirement changes

- Before coding behavior changes, make sure the updated requirement is recorded.
- Keep implementation aligned to one requirement set at a time.
- Record updates in `.agents/requirements.md` with `Change from` and `Reason`.
- If a requirement is replaced, do not keep old behavior behind toggles or dual paths.
- Update tests to lock in the new expected behavior and remove obsolete assertions.
- If the change alters API, config, CI, security, or workflow, update the smallest relevant docs.

## Mid-PR change handling

1. Stop adding new code while the requirement is being redefined.
2. Update the requirement record and ADR/documentation needs.
3. Refactor code to match the new requirement, deleting outdated logic.
4. Verify with tests and run the relevant gate(s) before commit.

## Archiving and splitting

If active entries in one topic become noisy or exceed five:

- create/append a topic file under `.agents/requirements/<topic>.md`.
- keep `requirements.md` as the short authoritative index with a pointer.
- link all topic files from `.agents/requirements/INDEX.md`.
