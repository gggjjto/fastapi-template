---
doc_type: architecture
status: active
authority: normative
scope: agent-harness
last_reviewed: 2026-08-12
---

# Harness Engineering

## 目标

Harness 让不同 coding agents 在同一仓库中读取相同约束、执行相同门禁，并避免把运行时状态或工具专属规则写进项目。

## 权威边界

| 关注点 | 权威来源 |
| --- | --- |
| Agent 入口、命令、架构地图、完成契约 | `AGENTS.md` |
| 工作流与技能路由 | `.agents/README.md`、`.agents/skills/` |
| 可复用执行规则 | `.agents/rules/` |
| 当前未完成需求 | `.agents/requirements.md` |
| 文档路由与生命周期 | `docs/README.md` |
| 确定性结构校验 | `scripts/check_ai_workflow.py` |
| Harness 行为评估 | `.agents/evals/`、`scripts/run_harness_evals.py` |

`.omx/` 是可选运行时状态，不提交到 Git。不要新增 `.claude`、`.codex` 或其他平行工作流真源。

## 确定性门禁

`make harness-check` 执行：

1. 必需 Harness 文件存在；
2. 禁止的工作流目录或引用不存在；
3. `.agents` 索引、活跃需求生命周期和 skill metadata 有效；
4. `docs/` 元数据、目录覆盖、权威组合和内部链接有效；
5. 后端 repository/service/core 导入边界有效；
6. 固定 Harness eval catalog 全部通过。

模型驱动的 live eval 是可选人工操作，不属于日常 CI 门禁。

## 提升条件

只有出现真实失败证据时才增加 Harness 能力：

- Web 出现真实用户旅程后增加浏览器验证；
- 出现可查询的本地可观测栈后增加日志/指标/trace 工具；
- 复现并行 worktree 端口冲突后增加服务隔离；
- 确定性规则无法捕捉重复文档漂移后再考虑语义检查。

不要提交 agent transcript、凭证、`.env`、临时评估 workspace 或运行时状态。
