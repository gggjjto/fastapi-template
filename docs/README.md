---
doc_type: index
status: active
authority: normative
scope: documentation-system
last_reviewed: 2026-08-12
---

# 文档入口

这里是仓库的人类与 AI 共同知识层。文档解释边界、契约和原因；代码、测试、迁移与配置描述当前实际行为。

## 先判断问题，再选择来源

| 问题 | 权威来源 |
| --- | --- |
| 当前代码做什么 | 代码、测试、迁移、配置 |
| AI 修改代码时必须遵守什么 | `AGENTS.md` 与 `.agents/` |
| 当前要实现什么 | 用户请求与 `.agents/requirements.md` |
| 系统如何分层 | [architecture.md](architecture.md) |
| 后端契约是什么 | [backend.md](backend.md) |
| 前端现在承担什么 | [frontend.md](frontend.md) |
| 如何开发和验证 | [development.md](development.md) |
| 如何运行、部署和发布 | [operations.md](operations.md) |
| 为什么采用某项长期决策 | [adr/README.md](adr/README.md) |
| Harness 如何约束 AI 与文档 | [harness-engineering.md](harness-engineering.md) |

当文档与可执行事实冲突时，以可执行事实为准并同步修正文档。历史和被替代的文档只能用于理解背景，不能指导当前实现。

## 文档目录

| 文档 | 类型 | 权威 | 范围 |
| --- | --- | --- | --- |
| [文档入口](README.md) | index | normative | 信息路由与冲突规则 |
| [系统架构](architecture.md) | architecture | normative | workspace 与运行时边界 |
| [后端契约](backend.md) | convention | normative | FastAPI、数据、认证、crawler |
| [前端边界](frontend.md) | convention | normative | Next.js 当前范围与扩展边界 |
| [开发与验证](development.md) | runbook | supporting | 本地开发和质量门禁 |
| [运行与发布](operations.md) | runbook | supporting | Docker、CI、迁移、发布 |
| [Harness Engineering](harness-engineering.md) | architecture | normative | AI 工作流治理 |
| [ADR 索引](adr/README.md) | index | normative | 决策生命周期 |
| [ADR 模板](adr/template.md) | template | normative | 新决策格式 |
| [ADR-0001](adr/0001-use-agents-as-ai-workflow-source.md) | adr | supporting | `.agents` 单一工作流来源 |
| [ADR-0002](adr/0002-documentation-as-a-governed-knowledge-system.md) | adr | supporting | 文档知识系统 |

## 元数据与生命周期

每份文档必须声明 `doc_type`、`status`、`authority`、`scope` 和 `last_reviewed`。

- `active`：当前有效。
- `draft`：提案，不能作为规范。
- `historical`：历史上下文，只能是 `reference`。
- `superseded`：已被其他文档替代，只能是 `reference`。
- `normative`：范围内必须遵守。
- `supporting`：用于操作和解释，不覆盖规范或代码事实。
- `reference`：仅供背景查询。

新增、删除或重命名文档时必须更新本目录，并运行 `make harness-check`。
