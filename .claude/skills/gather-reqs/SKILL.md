---
description: Gather and record feature requirements before coding. Use at the start of any new feature or significant change to surface ambiguities early and save a structured record.
disable-model-invocation: true
---

# Gather Requirements

Use this skill before starting a new feature or significant change. Goal: produce a clear, agreed spec that `/feature` can consume directly, and save it to `.claude/requirements.md`.

## Workflow

### Step 1 — Ask the right questions

Collect answers to these before writing anything:

| Question | Why it matters |
|---|---|
| What is the domain / feature name? | Determines file location and naming |
| What endpoints are needed? (method + path) | Scopes the work |
| What are the request fields, types, and validation rules? | Prevents schema rework |
| Is authentication required? Who can access it? | Auth is hard to add retroactively |
| What are the error cases and their HTTP codes? | Shapes exception and test design |
| What does a success response look like? | Sets the contract |
| Does it need a database model or migration? | Determines if Alembic is in scope |
| Any background jobs or cache involved? | Surfaces Redis/arq dependency |

Do not move on until every question has a clear answer. If the user is unsure about something, help them decide — offer a recommendation with a tradeoff, not an open question.

### Step 2 — Confirm the spec

Restate the agreed requirements in one short block:

```
Domain: <name>
Endpoints: <METHOD /path — one line each>
Auth: <public | CurrentUser | other>
Fields: <field: type, constraints>
Errors: <case → HTTP code>
Response: <shape of data>
Migration: <yes | no>
```

Ask: "Does this look right before we start coding?"

### Step 3 — Save to requirements log

Append to `.claude/requirements.md`:

```
### <Domain / Feature> — <YYYY-MM-DD>
**Requirement:** <one-sentence description of what was decided>
**Reason:** <why — business need, user request, constraint>
```

One entry per agreed requirement or decision. Do not write code until this step is done.

## Output

Return:

1. The confirmed spec block.
2. Confirmation that `.claude/requirements.md` was updated.
3. Next step: run `/feature` with the spec.
