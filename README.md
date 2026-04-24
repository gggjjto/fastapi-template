# FastAPI Template

一个偏现代、可直接二次开发的 FastAPI 后端模板，目标是“开箱即用 + 结构清晰 + 适合长期演进”。

## 特性

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 Async
- Alembic 迁移支持
- 分层结构：API / Service / Repository / Model
- `pydantic-settings` 配置管理
- `structlog` 结构化日志
- `pytest` 异步测试
- `ruff` + `mypy` + `pre-commit`
- Docker / docker-compose 示例
- 默认使用 SQLite 快速启动，也可切换 PostgreSQL

## 推荐目录结构

```text
app/
├── api/                # 路由层
├── core/               # 配置、日志、异常
├── db/                 # Base、Session、数据库初始化
├── models/             # SQLAlchemy 模型
├── repositories/       # 数据访问层
├── schemas/            # Pydantic DTO
├── services/           # 业务逻辑层
└── main.py             # 应用入口
```

## 快速开始

### 1. 准备环境

建议使用 `uv`：

```bash
uv venv
source .venv/bin/activate
uv sync --dev
cp .env.example .env
```

### 2. 启动开发服务器

```bash
uv run uvicorn app.main:app --reload
```

打开：

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 常用命令

```bash
make dev          # 本地开发
make lint         # Ruff 检查
make format       # Ruff 格式化
make typecheck    # mypy 类型检查
make test-up      # 启动测试依赖（PG + Redis）
make test         # 运行测试
make test-down    # 停止并清理测试依赖
make cov          # 运行测试并生成覆盖率
make ci           # 本地一键跑完整套 CI 检查
make migrate      # Alembic 升级到最新
make docker-build # 构建 Docker 镜像
```

## 测试

测试是**集成测试**，依赖真实 PostgreSQL + Redis，以真实覆盖数据库查询、缓存、任务队列等外部交互。

```bash
make test-up   # docker compose -f docker-compose.test.yml up -d --wait
make test
make test-down # 停止容器（tmpfs 存储，重启即净）
```

测试容器与主 `docker-compose.yml` 隔离：

| 组件 | 端口 | 数据库 | 持久化 |
|---|---|---|---|
| PostgreSQL | `localhost:5433` | `app_test` | tmpfs（容器关闭即清） |
| Redis | `localhost:6380` | 0 | 无 RDB / AOF |

每个测试开始前，`conftest.py` 的 autouse fixture 会自动：

- `drop_all + create_all` 重建所有表
- `FLUSHDB` 清空 Redis

通过 `asgi-lifespan` 触发 app lifespan，测试中真正初始化了 `RedisClient` 和 `ArqPool`，覆盖了生产路径。

## CI/CD

本模板提供一套开箱即用的 GitHub Actions 工作流，位于 `.github/workflows/`：

| 工作流 | 触发条件 | 作用 |
|---|---|---|
| `ci.yml` | push/PR → `main` | Ruff lint + format、mypy、pytest + 覆盖率（PG + Redis services）、Alembic 升/降级、Docker 构建验证 |
| `docker.yml` | push → `main`、`v*.*.*` tag | 构建 `linux/amd64` + `linux/arm64` 多架构镜像并推送到 GHCR，附带 SBOM 与构建 attestation |
| `release.yml` | 推送 `v*.*.*` tag 或手动触发 | 基于 commit 历史自动生成 Changelog 并创建 GitHub Release |

另外还提供：

- `.github/dependabot.yml`：每周一自动为 `uv`、`github-actions`、`docker` 生成依赖升级 PR（次要/补丁合并为一个 PR）
- `.dockerignore`：最小化构建上下文
- 多阶段 `Dockerfile`：基于 `uv` 构建，运行阶段非 root 用户，带 `HEALTHCHECK`

### 本地快速验证 CI

```bash
make ci           # 等价于 lint + format-check + typecheck + cov
docker build .    # 验证镜像能否构建
```

### 镜像地址

推送到 `main` 或打 `v*.*.*` tag 后，镜像会发布至：

```
ghcr.io/<owner>/<repo>:latest
ghcr.io/<owner>/<repo>:<version>
ghcr.io/<owner>/<repo>:sha-<short>
```

> 初次使用需在仓库 **Settings → Actions → General → Workflow permissions** 中勾选 **Read and write permissions**，以便 `GITHUB_TOKEN` 能推送到 GHCR。

## PostgreSQL 切换

将 `.env` 中的数据库配置改为：

```env
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app
APP_DB_CREATE_TABLES_ON_STARTUP=false
```

然后使用 Alembic：

```bash
uv run alembic revision --autogenerate -m "init"
uv run alembic upgrade head
```

## API 示例

### 健康检查

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

### 用户示例

- `POST /api/v1/users`
- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`

## 适合继续扩展的方向

- JWT / OAuth2 认证
- Redis 缓存
- Celery / Arq / Dramatiq 异步任务
- OpenTelemetry 链路追踪
- 多环境配置拆分
- 权限系统 / 租户系统

## 设计取舍

- **默认 SQLite**：方便本地 30 秒启动
- **保留 Alembic**：方便后续切换生产数据库
- **保留分层**：小项目也不会太重，大项目更容易演进
- **不预置复杂认证**：模板先保持干净，按业务再加
