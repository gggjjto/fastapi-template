---
doc_type: index
status: active
authority: normative
scope: architecture-decisions
last_reviewed: 2026-08-12
---

# Architecture Decision Records

ADR 只记录昂贵、长期且需要解释“为什么”的决定。当前实现细节写进代码和测试；活跃需求写进 `.agents/requirements.md`。

## Index

| ADR | Decision | Status | Date |
| --- | --- | --- | --- |
| [0001](0001-use-agents-as-ai-workflow-source.md) | Use `.agents` as the AI workflow source | Accepted | 2026-06-05 |
| [0002](0002-documentation-as-a-governed-knowledge-system.md) | Govern documentation as a knowledge system | Accepted | 2026-08-12 |

## Lifecycle

`Proposed → Accepted → Deprecated or Superseded`

- 不修改已接受 ADR 的决定；用新 ADR 替代它。
- ADR 被替代后更新状态和双向引用。
- 新 ADR 从 [template.md](template.md) 开始，并加入本索引及 `docs/README.md`。
