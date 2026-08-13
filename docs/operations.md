---
doc_type: runbook
status: active
authority: supporting
scope: runtime-and-delivery
last_reviewed: 2026-08-12
---

# 运行与发布

## 本地 Compose

`apps/api/docker-compose.yml` 提供 API、worker、crawler dispatcher、PostgreSQL 16 和 Redis 7。它面向开发：挂载源码并为 API 启用 reload，不是生产编排文件。

```bash
cd apps/api
docker compose up
```

数据库 migration 需要显式执行；Compose 不替代 Alembic。

## 容器镜像

`apps/api/Dockerfile` 使用多阶段构建、非 root 用户和 HTTP healthcheck。镜像默认只启动 API；worker 与 dispatcher 通过覆盖 command 复用镜像。

```bash
make api-docker-build
make api-docker-run
```

生产环境必须分别运行 API、worker 和 dispatcher，并由平台注入 secrets。不要保留开发 volume 或 `--reload`。

## CI

`.github/workflows/ci.yml` 在 push/PR 上执行：

- Ruff 与格式检查；
- AI workflow guard 与确定性 Harness evals；
- mypy；
- Web lint、typecheck、build；
- pip-audit 与 Bandit；
- PostgreSQL/Redis 集成测试与 coverage；
- Alembic upgrade 和 downgrade；
- Docker build、smoke test 与 Trivy HIGH/CRITICAL 扫描。

## 发布

`.github/workflows/release.yml` 在 `v*.*.*` tag 或手动输入 tag 时生成 GitHub Release 和 changelog。

当前发布流程不会推送容器镜像、部署环境、生成 SBOM、签名制品或自动执行生产 migration。不要在文档或 UI 中声称这些能力已经存在。

## 生产检查

- 运行 Alembic migration 后再切换 API 流量。
- 使用 `/api/v1/health/live` 做 liveness，`/api/v1/health/ready` 做 readiness。
- 显式配置 PostgreSQL、CORS、JWT secret 和 JSON 日志。
- Redis 与 Sentry 是可选能力；未配置时必须保持应用可运行。
- 回滚前确认 migration 是否可安全 downgrade；数据库变更优先采用兼容的 expand/contract 顺序。
