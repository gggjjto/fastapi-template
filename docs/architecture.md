---
doc_type: architecture
status: active
authority: normative
scope: repository-architecture
last_reviewed: 2026-08-17
---

# 系统架构

## 仓库定位

这是一个 pnpm + Turborepo 管理的快速开发 workspace，包含生产导向的 FastAPI 后端、可独立运行的 Next.js 前端骨架、共享 TypeScript 配置和仓库级 AI Harness。

```text
rapid-development-template/
├── apps/api/       FastAPI、多租户、Crawler、Hatchet 运行进程
├── apps/admin/     Next.js 平台管理后台
├── apps/web/       Next.js 业务前端空白骨架
├── packages/config 共享 TypeScript 与 ESLint 配置
├── .agents/        AI 工作流、规则、活跃需求、技能
├── docs/           人类与 AI 共同知识层
└── scripts/        Harness、doctor 与评估脚本
```

根 `Makefile` 提供统一入口；JavaScript workspace 任务交给 Turbo，API 任务交给 `apps/api/Makefile`。

## 运行单元

| 单元 | 入口 | 职责 |
| --- | --- | --- |
| API | `apps/api/app/main.py` | HTTP、生命周期、错误处理、中间件 |
| Worker | `apps/api/app/worker.py` | 注册并运行 Hatchet tasks |
| Crawler dispatcher | `apps/api/app/crawler/runtime/dispatcher.py` | PostgreSQL 待派发任务到 Hatchet |
| Crawler scheduler | `apps/api/app/crawler/runtime/scheduler.py` | 从 PostgreSQL 领取到期 Cron 计划并创建任务 |
| Admin | `apps/admin/src/app/` | 多租户、用户和 Crawler 管理后台；通过 BFF 访问 API |
| Web | `apps/web/src/app/` | 独立业务应用骨架；当前不调用 API |
| PostgreSQL | Alembic + SQLAlchemy | 持久状态和任务 outbox |
| Redis | 可选 | 缓存基础设施与 readiness 检查 |

API、worker、dispatcher 和 scheduler 可使用同一镜像，但必须作为独立进程运行。FastAPI 不依赖 Hatchet 凭证启动。

## 后端依赖方向

```text
router / dependencies
        ↓
service / application
        ↓
repository / persistence
        ↓
PostgreSQL, Redis, external runtimes
```

- Router 处理 HTTP 和 DTO，不承载业务流程。
- Service/Application 处理业务事务，不导入 FastAPI。
- Repository/Persistence 处理查询与持久化，不导入 HTTP 层。
- `app/core` 和 `app/db` 是基础设施层，不能反向依赖业务 domain。
- Crawler 进一步拆为 `domain`、`application`、`persistence`、`runtime`、`network` 和 `handlers`。

## 关键运行流

### HTTP

`main.py` → `app/router.py` → domain router → service → repository → database。

### Crawler

Cron scheduler 或租户 API 创建带幂等键的 job → PostgreSQL 保存 pending job → dispatcher 租约领取 → Hatchet 提交 → runner 按 job ID 加载 target → 已注册 handler 使用安全 HTTP client 抓取 → 结果回写 PostgreSQL。

租户、membership、invitation、Crawler target 和 job 都以 PostgreSQL 为事实来源；租户资源查询必须包含 `tenant_id` 约束。

## 扩展规则

- 新业务优先增加 `apps/api/app/<domain>/`，保持模块化单体。
- 只有实际消费者出现时才新增共享 package。
- 只有真实用户旅程出现时才引入前端 API client、状态管理或浏览器测试。
- 不为了未来拆分提前引入微服务、消息总线或额外存储。
