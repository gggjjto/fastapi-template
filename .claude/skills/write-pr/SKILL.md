---
description: 根据当前分支的 git diff 和 commit 自动生成 PR 描述。在所有质量门控通过后、推送前使用。
disable-model-invocation: true
---

# Write PR

读取当前分支的变更，生成填好的 PR 描述，准备直接粘贴或用 `gh pr create`。

## 步骤

1. 读取分支信息：

```bash
git log main..HEAD --oneline
git diff main..HEAD --stat
```

2. 读取变更细节（按需）：

```bash
git diff main..HEAD -- app/ tests/
```

3. 检查 `.claude/requirements.md` 中是否有对应的需求记录，用于补充背景。

4. 生成 PR 描述，填入 `.github/pull_request_template.md` 的每个字段：

```markdown
## Summary

- <一句话说明这个 PR 做了什么，面向 reviewer，不是面向用户>
- <如果有多个逻辑变更，每条一行>

## Changes

- <具体文件级别的变更，说明 why 不只是 what>
- <例：app/orders/service.py — 添加库存扣减逻辑，在事务中执行避免超卖>

## Validation

- `make lint`
- `make format`
- `make typecheck`
- `make test`（需要 `make test-up`）
- <如果有额外验证步骤，补充在这里>

## Checklist

- 变更范围聚焦且可回滚
- 若有数据库模型变更，已附 Alembic migration
- 若影响接口/行为，已更新文档或说明不需要
```

## 输出规则

- Summary 面向 reviewer，说"做了什么"和"为什么"
- Changes 每条说一个文件或模块，重点是 **why**，不是重复文件名
- 不写废话（"updated code"、"fixed issues"）
- 如果是多个 commit，合并成一个连贯的描述，不是 commit 列表的翻译

## 完成后

输出完整 PR 描述，然后询问："要直接用 `gh pr create` 提交吗？"

如果是，运行：

```bash
gh pr create --title "<title>" --body "<generated body>"
```
