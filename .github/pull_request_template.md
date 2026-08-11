## Summary

- 

## Changes

- 

## Validation

- `pnpm lint`
- `pnpm typecheck`
- `pnpm build`
- `make api-lint`
- `make api-format-check`
- `make api-typecheck`
- `make api-test` (with `make api-test-up`)

## AI Workflow

- [ ] `.agents/requirements.md` updated, or not needed
- [ ] ADR added/updated for significant decisions, or not needed
- [ ] Community skills installed/updated with `npx skills` are recorded in `skills-lock.json`
- [ ] No new tool-specific AI rule directories were introduced

## Harness Engineering

- [ ] Source-of-truth ownership changed, or not applicable
- [ ] New stable rule is mechanically checked, or the reason it remains guidance is stated
- [ ] Generated-project contract updated and tested, or not applicable
- [ ] Deterministic/live eval case added, or the reason no case is needed is stated
- [ ] Setup, API, configuration, test, CI, security, and Harness docs reviewed

## Checklist

- 变更范围聚焦且可回滚
- 若有数据库模型变更，已附 Alembic migration
- 若影响接口/行为，已更新文档或说明不需要
