# Harness Engineering

## Architecture

`AGENTS.md` is the entry map, `.agents/` owns rules, active requirements, and
on-demand skills, and `scripts/check_ai_workflow.py` enforces stable structural
invariants. `.omx/` is optional runtime state and is not part of this project.

## Ownership

- `AGENTS.md` — entry map and completion contract.
- `.agents/README.md` and `.agents/rules/INDEX.md` — workflow and rule indexes.
- `.agents/requirements.md` — active requirements only.
- `templates/*/template.json` and `scripts/create_project.py` — upstream template
  generator contract.
- `scripts/check_ai_workflow.py` — deterministic Harness enforcement.

## Quality status

Run `make harness-check` for required deterministic checks. Run
`make harness-eval` manually for optional model-backed evaluation. This generated
project has no inherited live-evaluation status; establish evidence in its own
environment before describing the live suite as healthy.

## Promotion triggers

- Add browser verification after the web app gains a real user journey.
- Add telemetry query tooling after the product has a local observability stack.
- Schedule live evaluations only after ten local runs reach at least 90%
  infrastructure reliability and credential/cost ownership is documented.

Do not commit raw agent transcripts, credentials, `.env` files, `.omx` state, or
temporary evaluation workspaces.
