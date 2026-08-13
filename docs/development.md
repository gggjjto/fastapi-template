---
doc_type: runbook
status: active
authority: supporting
scope: local-development
last_reviewed: 2026-08-12
---

# 开发与验证

## 首次安装

需要 Python 3.12+、uv、Node.js、pnpm 10 和 Docker。

```bash
pnpm install
make api-install
cp apps/api/.env.example apps/api/.env
make doctor
```

## 本地运行

```bash
make api-test-up
make api-migrate
make api-dev
make web-dev
```

可选进程：

```bash
HATCHET_CLIENT_TOKEN=... make api-worker
HATCHET_CLIENT_TOKEN=... make api-crawler-dispatcher
```

API 默认监听 `http://127.0.0.1:8000`，Web 默认监听 `http://localhost:3000`。

## 质量门禁

| 范围 | 命令 | 说明 |
| --- | --- | --- |
| 仓库 Harness | `make harness-check` | 结构、文档契约和确定性评估 |
| 后端 | `make api-ci` | Ruff、format、mypy、Harness、coverage |
| 后端测试服务 | `make api-test-up` / `make api-test-down` | PostgreSQL 5433、Redis 6380 |
| 前端 | `make web-lint web-typecheck web-build` | ESLint、TypeScript、Next build |
| Workspace | `make lint typecheck test build` | Turbo 任务图 |

单个后端测试从 `apps/api` 运行：

```bash
uv run pytest tests/path/test_file.py::test_name -v
```

API 集成测试依赖真实 PostgreSQL 和 Redis。不能启动服务时，只能报告已运行的静态或单元检查，不能声称完整测试通过。

## 变更完成条件

- 行为变化有最小回归测试。
- 模型变化包含 migration。
- 设置、API、部署、CI、安全或架构变化同步更新对应文档。
- 先运行能证明改动的最小测试，再运行受影响的 lint/type/build 门禁。
