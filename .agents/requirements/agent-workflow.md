# AI Workflow and Requirement Change Governance

This file defines how we keep requirements consistent when requests evolve during
implementation.

## Why this exists

In real development, requirements change after tests, design checks, or PR feedback.
Without a single update path, old logic or outdated assumptions drift into code.

We keep three authoritative layers:

1. `requirements.md` – current active requirements, short format.
2. `docs/adr/*.md` – long-lived architectural choices that affect multiple PRs.
3. `docs/*` and `.agents/rules/*` – operational and technical context.

The active requirements file is updated first. ADRs and docs are updated when the
change is durable enough to outlive the PR.

## Requirement state model

- `Proposed`: decision is captured and ready for implementation approval.
- `Accepted`: actively used by implementation.
- `Revised`: supersedes a prior requirement, and the prior entry is replaced with a "Change from" field.
- `Superseded`: no longer active, replaced by a newer requirement in history.
- `Archived`: intentionally abandoned.

## Change procedure for requirement updates

1. Confirm the user decision and list the impacted behaviors, error cases, and data model implications.
2. Add or update one entry in `requirements.md` with:
   - `Requirement`
   - `Change from` (if replacing)
   - `Reason`
   - `Status`
3. If the change affects existing domain behavior, remove old branch logic and implement the new behavior directly.
4. Update tests that prove old behavior is removed and new behavior is enforced.
5. Mention scope in PR summary and ADR/docs if needed.

## "Change happened mid-implementation" playbook

- Pause feature writing and align the requirement before continuing.
- Replace old decisions, do not add compatibility shims.
- Do not merge legacy paths as default fallback.
- Keep one final "current state" requirement entry.
- Add an inline test that fails on the obsolete behavior.

## Stability rule for `.agents` documents

When requirements become dense:

- Keep `requirements.md` small and index-like.
- Move detailed process into domain files under `.agents/requirements/`.
- Keep every move referenced from `.agents/requirements/INDEX.md`.

