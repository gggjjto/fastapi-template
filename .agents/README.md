# Agent Workflow

This directory is the single source of truth for AI-assisted development in this
repository.

## Layout

- `skills/` contains executable workflows and community skills in `SKILL.md`
  format.
- `rules/` contains reusable project rules referenced by skills and agents.
- `requirements.md` tracks active requirements and decisions that AI agents must
  preserve while implementing changes.

Prefer `.agents` over tool-specific directories such as `.claude` or `.codex`.
Tool-specific files may exist for compatibility, but they should point back to
this directory instead of becoming a separate source of truth.

## Community Skills

Use `npx skills` to discover, preview, install, update, and remove community
skills.

```bash
# Search
npx skills find fastapi
npx skills find pytest
npx skills find code review

# List skills in a source repository without installing
npx skills add fastapi/fastapi --list

# Preview one skill without installing
npx skills use fastapi/fastapi@fastapi --skill fastapi

# Install into this project's .agents/skills directory
npx skills add fastapi/fastapi --skill fastapi --agent codex --copy -y

# List project-installed skills
npx skills list --json

# Update project-installed skills
npx skills update -y
```

Always install project skills with `--agent codex --copy -y`. In this workspace,
that writes to `.agents/skills/<skill>/` and updates `skills-lock.json`.

Do not use `--agent "*"`. It installs to many agent-specific directories and
creates avoidable repository noise.

## Installed Community Skills

The currently recorded community skills are tracked in `../skills-lock.json`:

- `fastapi` from `fastapi/fastapi`
- `documentation-and-adrs` from `addyosmani/agent-skills`
- `architecture-decision-records` from `wshobson/agents`
- `code-review-excellence` from `wshobson/agents`
- `devops-deployment` from `yonatangross/orchestkit`
- `deployment-pipeline` from `hieutrtr/ai1-skills`
- `observability-engineer` from `sickn33/antigravity-awesome-skills`
- `incident-response` from `anthropics/knowledge-work-plugins`
- `backup-disaster-recovery` from `aj-geddes/useful-ai-prompts`
- `vulnerability-scanning` from `aj-geddes/useful-ai-prompts`
- `agent-builder` from `shareai-lab/learn-claude-code`
- `agent-orchestration` from `yonatangross/orchestkit`

Review every community skill before using it. Skills run with the same filesystem
and tool permissions as the active agent.
