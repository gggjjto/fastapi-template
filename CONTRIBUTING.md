# Contributing

感谢你愿意改进这个模板。该项目优先追求快速迭代与清晰约定，欢迎小步提交、快速评审。

## 快速开始

```bash
uv sync --dev
cp .env.example .env
make ci
```

如果需要跑集成测试（PostgreSQL + Redis）：

```bash
make test-up
make test
make test-down
```

## 分支与提交建议

- 分支命名：`feat/*`、`fix/*`、`chore/*`
- 提交信息：推荐 [Conventional Commits](https://www.conventionalcommits.org/)
- 单个 PR 尽量聚焦一个主题，方便回滚和复用

## Pull Request 最小检查清单

- `make lint` 通过
- `make format` 已运行
- `make typecheck` 通过
- `make test` 通过（需要先 `make test-up`）
- 涉及数据库模型变更时，包含对应 Alembic migration
- 变更了行为或接口时，README 或相关文档已同步

## 代码约定

- 目录结构采用 domain-oriented 组织（见 `CLAUDE.md`）
- 新增 API 时补充 `summary`、`description`、`response_model`
- 输入输出 schema 使用 `Field(description=..., examples=[...])`
- 优先小改动、可验证、可回退

