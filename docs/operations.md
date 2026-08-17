---
doc_type: runbook
status: active
authority: supporting
scope: runtime-and-delivery
last_reviewed: 2026-08-17
---

# 运行与发布

## 本地 Compose

`apps/api/docker-compose.yml` 的默认 profile 只启动 API、PostgreSQL 16 和 Redis 7。它面向开发：挂载源码并为 API 启用 reload，不是生产编排文件。

```bash
cd apps/api
docker compose up
```

Worker、dispatcher 和 scheduler 是独立进程，通过 operations profile 启动：

```bash
docker compose --profile operations up
```

数据库 migration 需要显式执行；Compose 中的 one-shot service 仍然调用 Alembic：

```bash
docker compose --profile tools run --rm migrate
```

## 容器镜像

`apps/api/Dockerfile` 基于 Python 3.12，使用多阶段构建、非 root 用户和 HTTP healthcheck。镜像默认只启动 API；worker、dispatcher 与 scheduler 通过覆盖 command 复用镜像。

```bash
make api-docker-build
make api-docker-run
```

生产环境必须分别运行 API、worker、dispatcher 和 scheduler，并由平台注入 secrets。不要保留开发 volume 或 `--reload`。

## CI

`.github/workflows/ci.yml` 在 push/PR 上执行：

- Ruff 与格式检查；
- AI workflow guard 与确定性 Harness evals；
- mypy；
- Admin/Web lint、typecheck、build；
- 从 `uv.lock` 导出的生产依赖执行 pip-audit，并运行 Bandit；
- PostgreSQL/Redis 集成测试与 coverage；
- Alembic upgrade、model drift check、单步 downgrade 和重新 upgrade；
- Docker build、smoke test 与 Trivy HIGH/CRITICAL 扫描。

## 发布

仓库当前没有发布工作流，因为还没有需要发布的稳定制品。需要推送容器镜像或部署环境时，再增加与真实 registry、环境审批、SBOM、签名和回滚策略对应的流程。

## 生产检查

- 运行 Alembic migration 后再切换 API 流量。
- 使用 `/api/v1/health/live` 做 liveness，`/api/v1/health/ready` 做 readiness。
- 显式配置 PostgreSQL、CORS、JWT secret 和 JSON 日志。
- Redis 与 Sentry 是可选能力；未配置时必须保持应用可运行。
- 回滚前确认 migration 是否可安全 downgrade；数据库变更优先采用兼容的 expand/contract 顺序。

## Crawler 可诊断查询

`crawl_jobs` 的 `dispatched_at`、`started_at`、`finished_at` 分别记录首次派发、首次执行和进入终态的时间。`finished_at` 有独立索引，支持以下按完成时间窗口过滤的 PostgreSQL 查询；阈值应按实际抓取周期调整。

生命周期日志按阶段使用不同事件名，避免把派发耗时、执行耗时和任务存活时间混为同一指标：

| 事件 | 含义 | 时长字段 |
| --- | --- | --- |
| `crawler.job.created` | 任务事务已提交 | 无 |
| `crawler.dispatch.succeeded` | 本次 Hatchet 提交已持久化 | `duration_ms`：本次提交耗时 |
| `crawler.dispatch.retrying` | 本次提交失败，重试状态已持久化 | `duration_ms`：本次提交耗时 |
| `crawler.dispatch.failed` | 本次提交进入终态失败且已持久化 | `duration_ms`：本次提交耗时 |
| `crawler.dispatch.lease_exhausted` | 最终租约过期且终态已持久化 | `job_age_ms`：创建到终态的总时长 |
| `crawler.dispatch.missing` | 已租用任务在提交结果时不存在 | `duration_ms`：本次提交耗时 |
| `crawler.execution.started` | 执行尝试已标记为运行中 | 无 |
| `crawler.execution.retrying` | 本次执行进入重试且已持久化 | `duration_ms`：本次执行尝试耗时 |
| `crawler.execution.succeeded` | 本次执行成功且已持久化 | `duration_ms`：本次执行尝试耗时 |
| `crawler.execution.failed` | 本次执行进入终态失败且已持久化 | `duration_ms`：本次执行尝试耗时 |

所有带 `attempt` 的事件都表示所属阶段的当前尝试次数；公共维度为 `crawl_job_id`、`handler_name` 和 `target_host`。终态日志只在对应事务提交成功后发出。

```sql
-- 当前状态分布
SELECT status, dispatch_state, count(*) AS jobs
FROM crawl_jobs
GROUP BY status, dispatch_state
ORDER BY status, dispatch_state;

-- pending / queued 中最老任务的等待时间
SELECT status, count(*) AS jobs, now() - min(created_at) AS oldest_age
FROM crawl_jobs
WHERE status IN ('pending', 'queued')
GROUP BY status;

-- 超过五分钟仍在执行的任务
SELECT id, tenant_id, started_at, now() - started_at AS running_for
FROM crawl_jobs
WHERE status = 'running' AND started_at < now() - interval '5 minutes'
ORDER BY started_at;

-- 最近一小时成功率
SELECT
  count(*) FILTER (WHERE status = 'succeeded') AS succeeded,
  count(*) FILTER (WHERE status = 'failed') AS failed,
  round(
    100.0 * count(*) FILTER (WHERE status = 'succeeded') / NULLIF(count(*), 0),
    2
  ) AS success_percent
FROM crawl_jobs
WHERE finished_at >= now() - interval '1 hour';

-- 最近一小时失败分类
SELECT error_category, error_code, count(*) AS failures
FROM crawl_jobs
WHERE status IN ('failed', 'cancelled') AND finished_at >= now() - interval '1 hour'
GROUP BY error_category, error_code;

-- 按 handler / host 统计最近一小时失败率
SELECT
  target.handler_name,
  target.target_host,
  count(*) AS finished,
  round(100.0 * count(*) FILTER (WHERE job.status = 'failed') / count(*), 2) AS failure_percent
FROM crawl_jobs AS job
JOIN crawl_targets AS target ON target.id = job.crawl_target_id
WHERE job.finished_at >= now() - interval '1 hour'
GROUP BY target.handler_name, target.target_host;

-- 最近一小时 P95 调度、排队、执行和端到端耗时（秒）
SELECT
  percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM dispatched_at - created_at)) AS dispatch_p95,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM started_at - dispatched_at)) AS queue_p95,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM finished_at - started_at)) AS execution_p95,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM finished_at - created_at)) AS total_p95
FROM crawl_jobs
WHERE finished_at >= now() - interval '1 hour';
```

业务 handler 应自行记录 `fetched`、`parsed`、`stored`、`rejected` 等计数，用于发现 HTTP 成功但数据为空或解析退化的情况。模板不约束 result 结构，也不判断具体业务数据质量。
