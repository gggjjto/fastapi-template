# Harness Engineering

## Architecture

The repository Harness is intentionally small: `AGENTS.md` is the entry map,
`.agents/` owns rules, active requirements, and on-demand skills, and
`scripts/check_ai_workflow.py` enforces stable structural invariants. Generated
projects receive the same repository-local contract. `.omx/` is optional runtime
state and is never part of the generated template.

## Source-of-truth ownership

| Concern | Authority |
| --- | --- |
| Agent entry map and completion contract | `AGENTS.md` |
| Rules and workflow index | `.agents/README.md`, `.agents/rules/INDEX.md` |
| Active requirements | `.agents/requirements.md` |
| Product architecture conventions | `docs/conventions/` |
| Generated-project contents | `templates/*/template.json`, `scripts/create_project.py` |
| Deterministic Harness enforcement | `scripts/check_ai_workflow.py` |
| Optional live-eval evidence | This document, after manual approval |

## Current quality status

- Repository-local Harness is copied into generated FastAPI projects.
- Product lint, type, build, and integration-test gates remain authoritative.
- Deterministic Harness checks are required; model-backed evaluations are manual.
- Latest approved live-eval summary (2026-07-20): `forbidden-workflow-path`
  passed on the first attempt in 82.153 seconds with zero changed files and zero
  policy violations. This single-case result proves the execution path; it does
  not yet establish the suite's >=80% health threshold.

## Promotion triggers

- Add browser verification after the web app gains a real user journey.
- Add logs, metrics, or traces query tooling after the product has a local
  observability stack.
- Add worktree-specific service isolation after the first reproduced port or
  resource collision.
- Add scheduled cleanup agents after two drift incidents escape deterministic
  checks.
- Consider scheduled live evaluations only after ten local suite runs reach at
  least 90% infrastructure reliability and credential/cost ownership is documented.

Do not commit raw agent transcripts, credentials, `.env` files, `.omx` state, or
temporary evaluation workspaces.
