<div align="center">

# FastAPI Template

**一个现代化、开箱即用、面向真实业务的 FastAPI 后端项目模板。**

[![CI](https://github.com/gggjjto/fastapi-template/actions/workflows/ci.yml/badge.svg)](https://github.com/gggjjto/fastapi-template/actions/workflows/ci.yml)
[![Docker](https://github.com/gggjjto/fastapi-template/actions/workflows/docker.yml/badge.svg)](https://github.com/gggjjto/fastapi-template/actions/workflows/docker.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#贡献)

</div>

---

## 简介

`fastapi-template` 是一个**按领域（domain-oriented）组织**的 FastAPI 后端脚手架，开箱提供生产环境常见基础设施：JWT 认证、Redis 缓存、Arq 任务队列、结构化日志、全局异常处理、限流、健康探针、统一响应格式，以及完整的测试 / CI / Docker 发布流水线。

适合用作：

- 新项目起步骨架
- 团队内部"最佳实践"参考实现
- 学习现代 FastAPI 工程化的示例

## 目录

- [特性](#特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [核心约定](#核心约定)
- [配置](#配置)
- [API 示例](#api-示例)
- [测试](#测试)
- [开发](#开发)
- [Docker 部署](#docker-部署)
- [CI/CD](#cicd)
- [路线图](#路线图)
- [贡献](#贡献)
- [许可证](#许可证)
- [致谢](#致谢)

## 特性

- **FastAPI + Pydantic v2** — 现代、高性能、强类型
- **异步 SQLAlchemy 2.0** + **Alembic** 迁移
- **JWT 认证**（access / refresh token）+ 受保护路由依赖
- **领域分层**：`router` / `service` / `repository` / `model` / `schemas`
- **统一响应封装** `ApiResponse[T]`：`{code, message, data}` 结构
- **全局异常处理** + 领域异常（`DomainError`、`ConflictError`...）
- **Redis 缓存** + **Arq 任务队列**（可选，通过 `APP_REDIS_URL` 开关）
- **限流**（slowapi）+ **结构化日志**（structlog，JSON 可选）
- **Request ID** 中间件，全链路日志绑定
- **Sentry** 错误追踪（可选）
- **健康探针**：`/live`、`/ready`（用于 K8s liveness / readiness）
- **可配置文档可见性**：非 dev/test 环境自动隐藏 OpenAPI
- **集成测试**：直接对接真实 PostgreSQL + Redis，不做 mock
- **完整 CI/CD**：lint / type-check / test / migrations / docker build & publish
- **多阶段 Dockerfile**：基于 `uv`，运行阶段非 root + healthcheck

## 技术栈

| 领域 | 选型 |
|---|---|
| Web 框架 | FastAPI, Pydantic v2 |
| ORM / 迁移 | SQLAlchemy 2.0 (async), Alembic |
| 数据库 | PostgreSQL（生产） / SQLite（快速启动） |
| 缓存 / 队列 | Redis, Arq |
| 认证 | PyJWT, bcrypt |
| 日志 | structlog |
| 限流 | slowapi |
| 错误追踪 | sentry-sdk |
| 包管理 | [uv](https://github.com/astral-sh/uv) |
| Lint / Format | ruff |
| 类型检查 | mypy |
| 测试 | pytest, pytest-asyncio, httpx, asgi-lifespan |
| 容器 | Docker, docker-compose |
| CI/CD | GitHub Actions, Dependabot, GHCR |

## 快速开始

### 环境要求

- Python `>= 3.12`
- [uv](https://github.com/astral-sh/uv) `>= 0.5`
- Docker + Docker Compose（仅运行测试 / 容器化部署时需要）

### 60 秒上手（SQLite，零外部依赖）

```bash
git clone https://github.com/gggjjto/fastapi-template.git
cd fastapi-template

uv sync --dev
cp .env.example .env

uv run uvicorn app.main:app --reload
```

打开：

- API: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

### 完整本地栈（PostgreSQL + Redis，容器化）

```bash
cp .env.example .env
docker compose up
```

启动后会同时拉起 API + PostgreSQL + Redis。适合本地验证生产路径。

## 项目结构

本项目采用 **domain-oriented** 结构：每个业务域（auth、users、health...）在自己的目录内自带 `router / service / repository / models / schemas / dependencies / exceptions / constants`，而不是按技术层横向切分。

```text
app/
├── auth/                   # JWT 认证域
│   ├── router.py           # POST /auth/token, /auth/refresh, GET /auth/me
│   ├── service.py          # 登录 / 刷新逻辑
│   ├── security.py         # 哈希密码、签发/解析 token
│   ├── dependencies.py     # get_current_user / CurrentUser
│   └── ...
├── users/                  # 用户域
│   ├── router.py
│   ├── service.py
│   ├── repository.py       # 数据访问层
│   ├── models.py           # SQLAlchemy ORM
│   ├── schemas.py          # Pydantic DTO
│   └── ...
├── health/                 # 健康探针
├── core/
│   ├── config.py           # pydantic-settings，所有 env 前缀 APP_
│   ├── response.py         # ApiResponse[T] 统一响应
│   ├── error_handlers.py   # 全局错误处理
│   ├── middleware.py       # RequestID 中间件
│   ├── limiter.py          # slowapi 限流
│   ├── pagination.py       # 通用分页
│   ├── cache.py            # RedisCache 封装
│   ├── arq.py              # Arq 连接池生命周期
│   ├── sentry.py           # Sentry 初始化
│   └── logging.py          # structlog 配置
├── db/
│   ├── base.py             # DeclarativeBase + 命名约定
│   ├── session.py          # async engine / session / reset_db
│   └── redis.py            # Redis 客户端生命周期
├── router.py               # 顶层路由，挂载到 /api/v1
├── main.py                 # create_app() 工厂 + lifespan
└── worker.py               # Arq Worker 入口
```

## 核心约定

> 更详细约定见 [CLAUDE.md](./CLAUDE.md)。

- **响应格式**：所有接口返回 `ApiResponse[T]`，即 `{"code": 200, "message": "success", "data": ...}`。路由中使用 `ApiResponse.ok(data)`。
- **环境变量**：一律 `APP_` 前缀，通过 `get_settings()`（LRU 单例）访问。
- **数据库会话**：使用 `DBSession` 类型别名，由 `get_db_session()` 依赖注入。
- **Redis / Arq**：仅当 `APP_REDIS_URL` 非空时启用；使用 `RedisClient` / `ArqPool` 类型别名。
- **限流**：使用 `@limiter.limit("N/period")` 装饰器，**首个参数必须是 `request: Request`**。
- **认证保护**：`CurrentUser = Annotated[User, Depends(get_current_active_user)]`。
- **异常分层**：Service 抛 `DomainError` 子类，Dependencies 直接抛 `HTTPException`，Router 负责把领域异常转为 HTTP 响应。
- **Pydantic 基类**：所有 Schema 继承 `CustomModel`（`populate_by_name=True`, `from_attributes=True`）。
- **文档可见性**：非 `development` / `test` 环境自动隐藏 OpenAPI（`openapi_url=None`）。

## 配置

所有配置通过 `.env` 文件或环境变量传入，统一使用 `APP_` 前缀。常用项：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | `development` / `staging` / `production` / `test` |
| `APP_DEBUG` | `true` | 调试模式 |
| `APP_DATABASE_URL` | `sqlite+aiosqlite:///./app.db` | 数据库连接 |
| `APP_DB_CREATE_TABLES_ON_STARTUP` | `true` | 启动时自动建表（SQLite 使用；PG 请用 Alembic） |
| `APP_JWT_SECRET` | ⚠️ 改掉 | 建议 `python -c "import secrets; print(secrets.token_hex(32))"` |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | access token 有效期 |
| `APP_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | refresh token 有效期 |
| `APP_REDIS_URL` | *(空)* | 留空则关闭 Redis、缓存、Arq |
| `APP_SENTRY_DSN` | *(空)* | 留空则关闭 Sentry |
| `APP_LOG_JSON` | `false` | 结构化日志输出为 JSON |
| `APP_ALLOWED_ORIGINS` | `["*"]` | CORS 白名单，逗号分隔 |

完整列表见 [`app/core/config.py`](./app/core/config.py) 与 [`.env.example`](./.env.example)。

### 切换到 PostgreSQL

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

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/health/live` | 存活探针（K8s liveness） |
| `GET` | `/api/v1/health/ready` | 就绪探针（校验数据库连接） |
| `POST` | `/api/v1/users` | 注册用户 |
| `GET` | `/api/v1/users` | 分页列出用户 |
| `GET` | `/api/v1/users/{user_id}` | 获取用户 |
| `POST` | `/api/v1/auth/token` | 登录，获取 access + refresh token |
| `POST` | `/api/v1/auth/refresh` | 使用 refresh token 换新 access token |
| `GET` | `/api/v1/auth/me` | 获取当前登录用户信息 |

## 测试

测试为**真集成测试**，依赖 PostgreSQL + Redis，最大限度覆盖生产路径。

```bash
make test-up   # 启动测试依赖容器（PG + Redis）
make test      # 运行 pytest
make test-down # 停止并清理
```

测试容器通过 `docker-compose.test.yml` 与 dev 栈隔离：

| 组件 | 端口 | 数据库 | 持久化 |
|---|---|---|---|
| PostgreSQL | `localhost:5433` | `app_test` | tmpfs（即开即清） |
| Redis | `localhost:6380` | DB 0 | 无 RDB / AOF |

每个测试执行前，`conftest.py` 的 autouse fixture 自动：

- `drop_all + create_all` 重建所有表
- `FLUSHDB` 清空 Redis

通过 `asgi-lifespan` 触发 app lifespan，测试真正会初始化 `RedisClient` / `ArqPool`。

## 开发

### 常用命令

```bash
make help         # 列出所有可用命令

make dev          # 开发服务器（uvicorn --reload）
make lint         # ruff check
make format       # ruff format
make typecheck    # mypy
make test         # 运行测试
make cov          # 测试 + 覆盖率报告
make ci           # 本地一键跑全套 CI 检查

make migrate              # alembic upgrade head
make revision m="init"    # 自动生成迁移

make docker-build # 构建镜像
make docker-run   # 本地运行镜像
```

### pre-commit

```bash
uv run pre-commit install
```

之后每次 `git commit` 都会自动运行 `ruff check` + `ruff format`。

## Docker 部署

### 构建 & 运行

```bash
docker build -t fastapi-template:latest .
docker run --rm -p 8000:8000 \
  -e APP_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))") \
  -e APP_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  -e APP_REDIS_URL=redis://host:6379/0 \
  -e APP_ENV=production \
  fastapi-template:latest
```

### 镜像特性

- 多阶段构建（builder + runtime）
- 基于 `uv` 安装依赖，带 BuildKit cache mount
- 运行阶段非 root 用户
- 内建 `HEALTHCHECK` 打到 `/api/v1/health/live`
- 多架构（`linux/amd64` + `linux/arm64`）

### GHCR 镜像

CI 会自动发布到 GitHub Container Registry：

```text
ghcr.io/gggjjto/fastapi-template:latest
ghcr.io/gggjjto/fastapi-template:<version>
ghcr.io/gggjjto/fastapi-template:sha-<short>
```

## CI/CD

完整 GitHub Actions 工作流位于 [`.github/workflows/`](./.github/workflows)：

| 工作流 | 触发 | 作用 |
|---|---|---|
| [`ci.yml`](./.github/workflows/ci.yml) | push / PR → `main` | Ruff lint + format、mypy、pytest + 覆盖率（PG + Redis services）、Alembic 升/降级、Docker 构建验证 |
| [`docker.yml`](./.github/workflows/docker.yml) | push → `main`、`v*.*.*` tag | 构建并发布多架构镜像到 GHCR，附带 SBOM 与构建 attestation |
| [`release.yml`](./.github/workflows/release.yml) | `v*.*.*` tag 或手动 | 基于 commit 历史自动生成 Changelog 并创建 GitHub Release |

配套：

- [`.github/dependabot.yml`](./.github/dependabot.yml) — 每周自动升级 uv / GitHub Actions / Dockerfile 依赖
- [`.dockerignore`](./.dockerignore) — 最小化镜像构建上下文

### 首次启用前的准备

1. 仓库 **Settings → Actions → General → Workflow permissions** 勾选 **Read and write permissions**（GHCR 推送需要）。
2. （可选）在 **Settings → Secrets and variables → Actions** 添加 `CODECOV_TOKEN` 启用覆盖率上传。

### 本地复现 CI

```bash
make ci           # 等价于 lint + format-check + typecheck + cov
docker build .    # 验证镜像构建
```

## 路线图

- [ ] OAuth2 / OIDC 第三方登录示例
- [ ] 细粒度权限（RBAC / Casbin）示例
- [ ] OpenTelemetry 链路追踪
- [ ] 多租户 / 多环境配置示例
- [ ] WebSocket 示例
- [ ] 事件驱动（domain events / outbox）示例

欢迎通过 [Issues](https://github.com/gggjjto/fastapi-template/issues) 讨论新方向。

## 贡献

欢迎 Issue 与 Pull Request！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/awesome`
3. 本地通过所有检查：`make ci`
4. 提交（推荐 [Conventional Commits](https://www.conventionalcommits.org/)）：`git commit -m "feat: add awesome"`
5. 推送并发起 PR

提交前请确保：

- [ ] `make lint` 通过
- [ ] `make format` 已运行
- [ ] `make test` 通过（需先 `make test-up`）
- [ ] 新代码补充了对应测试

## 许可证

本项目基于 [MIT License](./LICENSE) 开源 —— 可自由用于商业与个人项目。

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) — 项目的基石
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) — 领域化目录约定参考
- [astral-sh/uv](https://github.com/astral-sh/uv) 与 [astral-sh/ruff](https://github.com/astral-sh/ruff) — 现代 Python 工具链
- 所有依赖开源库的作者 — 没有你们就没有这个模板

---

<div align="center">

如果这个模板对你有帮助，欢迎给一个 [Star](https://github.com/gggjjto/fastapi-template/stargazers)

</div>
