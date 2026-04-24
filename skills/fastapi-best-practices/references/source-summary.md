# Source summary

This skill is derived from these upstream sources:

- Repository: https://github.com/zhanymkanov/fastapi-best-practices
- Agent-oriented summary: https://raw.githubusercontent.com/zhanymkanov/fastapi-best-practices/master/AGENTS.md
- Main guide: https://raw.githubusercontent.com/zhanymkanov/fastapi-best-practices/master/README.md

## Core ideas extracted from the source

### 1. Structure by scalability, not only by file type

The source emphasizes avoiding a flat structure that becomes hard to maintain as features grow. Favor feature-oriented or domain-aware layouts and keep route, schema, model, and service code logically grouped.

### 2. Be strict about async boundaries

The guide distinguishes clearly between non-blocking async work, blocking I/O, and CPU-bound work. Do not mark everything async by default. Pick `async def`, `def`, threadpool offloading, or a worker process based on the actual workload.

### 3. Use dependencies as composition points

The source leans heavily on FastAPI dependencies for reusable request-time logic such as auth checks, validation, parsing, and object loading.

### 4. Keep schemas and settings explicit

Use Pydantic models for clean boundaries. Avoid unclear abstraction layers. Keep environment-driven settings centralized and typed.

### 5. Treat database conventions as part of maintainability

Stable naming conventions, careful migration review, and pragmatic SQL usage make long-term maintenance easier.

### 6. Keep testing and linting close to daily development

Async tests, explicit API contracts, and fast lint/format feedback loops are treated as core engineering hygiene rather than optional polish.

## How to use this reference

Open this file when you need extra context for why the skill recommends a convention. For direct implementation instructions, prefer `../SKILL.md` first.
