---
description: 安全升级项目依赖。处理版本检查、约束确认、breaking change 分析、测试验证的完整流程。
disable-model-invocation: true
---

# Upgrade Dependencies

依赖升级的完整工作流，从检查到验证。

## 已知约束（升级前必查）

| 依赖 | 约束 | 原因 |
|---|---|---|
| `redis` | `<6` | `arq <=0.28` 不支持 redis 6/7，升级前确认 arq 已支持 |

升级任何依赖前，先检查它是否影响上表中的约束链。

## 步骤

### 1. 检查可升级的依赖

```bash
uv pip list --outdated
```

或针对单个包：

```bash
uv pip show <package>
```

### 2. 确认升级目标

明确：
- 升级哪个包，从什么版本到什么版本
- 是 patch（安全修复）、minor（新功能兼容）还是 major（可能有 breaking change）

### 3. 分析 breaking change

- 读取该包的 changelog 或 release notes（用 `gh` 或 WebSearch 查）
- Major 版本：找 migration guide，列出所有 breaking change
- Minor/patch：确认无 API 变更

### 4. 执行升级

修改 `pyproject.toml` 中的版本约束，然后：

```bash
uv sync --dev
```

### 5. 验证

按顺序运行，每步通过再执行下一步：

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
make test-up
make test
```

如果有 breaking change 导致的类型错误或运行时错误，在这一步修复，**不要用 `# type: ignore` 掩盖**。

### 6. 检查文档

如果升级影响：
- 配置方式（env var、settings）
- 部署依赖（Docker base image、系统依赖）
- 开发命令

按 `.claude/rules/docs-maintenance.md` 更新对应文档。

## 输出

返回：

1. 升级了哪个包，版本变化
2. Breaking change 列表（无则说明）
3. 修复了哪些代码（如有）
4. 质量门控结果
5. 文档是否需要更新
