---
description: Safe refactoring workflow. Use when restructuring existing code without changing behavior — establishes a test baseline before changes and verifies it holds after.
disable-model-invocation: true
---

# Refactor

安全重构流程：先建立测试基线，再改代码，再验证行为不变。

---

## 阶段一：确认范围

重构前先明确：

- 目标是什么？（命名、拆分函数、消除重复、调整层职责）
- 哪些文件会被改动？
- 行为是否必须完全不变？（通常是；如果允许行为变化，用 `/feature` 而不是这个流程）

---

## 阶段二：建立基线

运行当前测试，确认全部通过，记录结果：

```bash
uv run pytest tests/ -v
```

如果有测试失败，先用 `/fix-bug` 修复，不要在测试已经失败的状态下开始重构。

---

## 阶段三：做最小改动

- 每次只改一件事：先改名，或先拆函数，不要同时做多件事。
- 不添加新功能，不改变对外接口。
- 不修改与重构目标无关的代码。
- 如果发现其他问题，记录下来，等这次重构完成后单独处理。

使用 `code-reviewer` agent 检查改动是否清晰、有无层边界泄漏。

---

## 阶段四：验证行为不变

重新运行测试，结果必须与阶段二完全一致：

```bash
uv run pytest tests/ -v
```

如果有测试失败，说明重构改变了行为——回退并重新分析。

---

## 阶段五：质量检查

```bash
uv run ruff check --fix . && uv run ruff format .
uv run ruff check .
uv run mypy app
```

---

## 阶段六：提交

使用 `refactor:` 类型，描述做了什么结构调整：

```
refactor: extract pagination logic into shared repository helper
refactor: split UserService.create into validate + persist steps
```

不要把重构和功能变更混在同一个 commit。
