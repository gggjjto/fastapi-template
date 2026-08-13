---
doc_type: architecture
status: active
authority: normative
scope: repository-architecture
last_reviewed: 2026-08-12
---

# 系统架构

## 仓库定位

这是一个 pnpm + Turborepo 管理的快速开发 workspace，包含生产导向的 FastAPI 后端、可独立运行的 Next.js 前端骨架、共享 TypeScript 配置和仓库级 AI Harness。

```text
fastapi-template/
├── apps/api/       FastAPI、PostgreSQL、Redis、Hatchet worker
├── apps/web/       Next.js App Router 控制台骨架
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
| Web | `apps/web/src/app/` | 独立 Next.js 应用；当前不调用 API |
| PostgreSQL | Alembic + SQLAlchemy | 持久状态和任务 outbox |
| Redis | 可选 | 缓存基础设施与 readiness 检查 |

API、worker 和 dispatcher 可使用同一镜像，但必须作为独立进程运行。FastAPI 不依赖 Hatchet 凭证启动。

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

内部调用创建带租户与幂等键的 job → PostgreSQL 保存 pending job → dispatcher 租约领取 → Hatchet 提交 → runner 调用已注册 handler → 安全 HTTP client 抓取 → 结果回写 PostgreSQL。

Crawler 当前没有公开 HTTP API，也没有租户或 target 管理 API。

## 扩展规则

- 新业务优先增加 `apps/api/app/<domain>/`，保持模块化单体。
- 只有实际消费者出现时才新增共享 package。
- 只有真实用户旅程出现时才引入前端 API client、状态管理或浏览器测试。
- 不为了未来拆分提前引入微服务、消息总线或额外存储。
