---
description: 把大需求拆解成有序的小 PR。在 /discuss-reqs 确认规格后、/feature 开始前使用。
disable-model-invocation: true
---

# Breakdown

大需求拆成有序 PR 的工作流。每个 PR 应独立可审查、可回滚，且不超过一个逻辑变更单元。

## 输入

需要已有 `/discuss-reqs` 或 `/gather-reqs` 产出的确认规格。如果规格还不清楚，先运行 `/discuss-reqs`。

## 拆解原则

**按层依赖排序**，后层依赖前层：

```
1. 数据层   models.py + migration
2. 查询层   repository.py
3. 业务层   service.py + exceptions.py + constants.py
4. 接口层   schemas.py + router.py + dependencies.py
5. 测试层   tests/<domain>/
```

**一个 PR 只做一件事：**
- 不要把 model 变更和新端点混在一起
- migration 必须和 model 变更在同一个 PR，不能分开
- 测试可以和业务代码同一个 PR，也可以紧跟一个单独 PR

**判断拆还是不拆：**
- 单个端点 + 无 model 变更 → 一个 PR
- 新域（多个端点 + 新 model）→ 至少两个 PR（data layer 先）
- 影响多个现有域 → 按域分 PR，共享变更（如 core 修改）先出

## 输出格式

列出有序 PR 清单：

```
PR 1 — <标题>
  变更：<文件列表>
  原因：<为什么这个先做>
  依赖：<无 | 依赖 PR N>
  验证：<运行哪些命令>

PR 2 — <标题>
  ...
```

然后问："这个拆分方式你认可吗？从 PR 1 开始，运行 `/feature`。"

## 保存

拆解结果追加到 `.claude/requirements.md`：

```
### [Feature] 拆解计划 — YYYY-MM-DD
**PR 顺序：** PR1 → PR2 → ...
**Reason:** 说明拆分逻辑
```
