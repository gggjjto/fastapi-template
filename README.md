# FastAPI Template

**一个现代化、开箱即用、面向真实业务的 FastAPI 后端项目模板。**

[CI](https://github.com/gggjjto/fastapi-template/actions/workflows/ci.yml)
[Python](https://www.python.org/downloads/)
[License: MIT](./LICENSE)
[Ruff](https://github.com/astral-sh/ruff)
[uv](https://github.com/astral-sh/uv)
[PRs Welcome](#贡献)

---

## 简介

`fastapi-template` 是一个**按领域（domain-oriented）组织**的 FastAPI 后端脚手架，开箱提供生产环境常见基础设施：JWT 认证、Redis 缓存、Arq 任务队列与周期任务、结构化日志、全局异常处理、限流、健康探针、统一响应格式，以及完整的测试与 CI 流程。

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
- [AI 开发工作流](#ai-开发工作流)
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
- **统一响应封装** `ApiResponse[T]`：`{code, message, data, request_id}` 结构，`code` 为稳定字符串业务码
- **全局异常处理** + 领域异常（`DomainError` 携带 `code`/`status_code`，全局处理器统一转换）
- **Redis 缓存** + **Arq 任务队列 / 周期任务**（可选，通过 `APP_REDIS_URL` 开关）
- **限流**（slowapi）+ **结构化日志**（structlog，JSON 可选，自动遮蔽密码/令牌等敏感字段）
- **Request ID** 中间件：注入 `X-Request-ID`、绑定 `request_id`/`user_id` 到日志上下文，并为每个请求输出一条 `http.request` 访问日志
- **Sentry** 错误追踪（可选）
- **健康探针**：`/live`、`/ready`（用于 K8s liveness / readiness）
- **可配置文档可见性**：非 dev/test 环境自动隐藏 OpenAPI
- **集成测试**：直接对接真实 PostgreSQL + Redis，不做 mock
- **完整 CI**：lint / format-check / type-check / test / migrations / docker build 验证
- **多阶段 Dockerfile**：基于 `uv`，运行阶段非 root + healthcheck

## 技术栈


| 领域            | 选型                                           |
| ------------- | -------------------------------------------- |
| Web 框架        | FastAPI, Pydantic v2                         |
| ORM / 迁移      | SQLAlchemy 2.0 (async), Alembic              |
| 数据库           | PostgreSQL（生产） / SQLite（快速启动）                |
| 缓存 / 队列 / 定时任务 | Redis, Arq                                   |
| 认证            | PyJWT, bcrypt                                |
| 日志            | structlog                                    |
| 限流            | slowapi                                      |
| 错误追踪          | sentry-sdk                                   |
| 包管理           | [uv](https://github.com/astral-sh/uv)        |
| Lint / Format | ruff                                         |
| 类型检查          | mypy                                         |
| 测试            | pytest, pytest-asyncio, httpx, asgi-lifespan |
| 容器            | Docker, docker-compose                       |
| CI/CD         | GitHub Actions, Dependabot                   |


实践参考：[zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)。该仓库示例使用 `src/` 作为应用目录；本模板使用 `app/`，语义等价。面向 AI 的精简规则也可参考其 [AGENTS.md](https://github.com/zhanymkanov/fastapi-best-practices/blob/master/AGENTS.md)，本项目规则以 `.agents/rules/` 为准。

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

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 完整本地栈（PostgreSQL + Redis，容器化）

```bash
cp .env.example .env
docker compose up
```

启动后会同时拉起 API + Worker + PostgreSQL + Redis。适合本地验证生产路径。

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
│   ├── middleware.py       # RequestID 中间件 + http.request 访问日志
│   ├── limiter.py          # slowapi 限流
│   ├── pagination.py       # 通用分页
│   ├── cache.py            # RedisCache 封装
│   ├── arq.py              # Arq 连接池生命周期
│   ├── sentry.py           # Sentry 初始化
│   ├── logging.py          # structlog 配置 + 敏感字段遮蔽处理器
│   └── request_context.py  # 绑定/读取 request_id、user_id 等日志上下文
├── db/
│   ├── base.py             # DeclarativeBase + 命名约定
│   ├── session.py          # async engine / session / reset_db
│   └── redis.py            # Redis 客户端生命周期
├── router.py               # 顶层路由，挂载到 /api/v1
├── main.py                 # create_app() 工厂 + lifespan
└── worker.py               # Arq Worker 入口
```

## 核心约定

> 更详细约定见 [AGENTS.md](./AGENTS.md)。

- **响应格式**：所有接口返回 `ApiResponse[T]`，即 `{"code": "OK", "message": "success", "data": ..., "request_id": "..."}`。路由中使用 `ApiResponse.ok(data)`。错误响应由全局处理器生成，`code` 为稳定业务码（如 `USER_NOT_FOUND`、`AUTH_INVALID_CREDENTIALS`、`VALIDATION_ERROR`），`data` 为 `null`，并尽可能带上 `request_id`。`code` 是 API 契约，不被本地化；可本地化的是 `message`。
- **环境变量**：一律 `APP_` 前缀，通过 `get_settings()`（LRU 单例）访问。
- **数据库会话**：使用 `DBSession` 类型别名，由 `get_db_session()` 依赖注入。
- **Redis / Arq**：仅当 `APP_REDIS_URL` 非空时启用；使用 `RedisClient` / `ArqPool` 类型别名。
- **周期任务**：使用 `app/worker.py` 的 `WorkerSettings.cron_jobs` 注册 Arq cron job；worker 必须作为独立进程运行，且执行时间取决于 worker 进程时区。
- **限流**：使用 `@limiter.limit("N/period")` 装饰器，**首个参数必须是 `request: Request`**。
- **认证保护**：`CurrentUser = Annotated[User, Depends(get_current_active_user)]`。
- **异常分层**：Service / 领域守卫依赖抛 `DomainError` 子类（携带稳定 `code` 与 `status_code`），由全局处理器统一转换为响应信封；Router **不再手写** `try/except` 翻译领域异常。Token 解码等通用守卫仍可抛 `HTTPException`。
- **Pydantic 基类**：所有 Schema 继承 `CustomModel`（`populate_by_name=True`, `from_attributes=True`）。
- **文档可见性**：非 `development` / `test` 环境自动隐藏 OpenAPI（`openapi_url=None`）。
- **响应取舍**：统一 `ApiResponse[T]` 会让 FastAPI 按 `response_model` 再做一次响应校验；模板优先保证响应结构一致，性能极敏感接口可单独评估。

## 配置

所有配置通过 `.env` 文件或环境变量传入，统一使用 `APP_` 前缀。常用项：


| 变量                                | 默认值                            | 说明                                                            |
| --------------------------------- | ------------------------------ | ------------------------------------------------------------- |
| `APP_ENV`                         | `development`                  | `development` / `staging` / `production` / `test`             |
| `APP_DEBUG`                       | `true`                         | 调试模式                                                          |
| `APP_DATABASE_URL`                | `sqlite+aiosqlite:///./app.db` | 数据库连接                                                         |
| `APP_DB_CREATE_TABLES_ON_STARTUP` | `true`                         | 启动时自动建表（SQLite 使用；PG 请用 Alembic）                              |
| `APP_JWT_SECRET`                  | ⚠️ 改掉                          | 建议 `python -c "import secrets; print(secrets.token_hex(32))"` |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                           | access token 有效期                                              |
| `APP_REFRESH_TOKEN_EXPIRE_DAYS`   | `30`                           | refresh token 有效期                                             |
| `APP_REDIS_URL`                   | *(空)*                          | 留空则关闭 Redis、缓存、Arq                                            |
| `APP_SENTRY_DSN`                  | *(空)*                          | 留空则关闭 Sentry                                                  |
| `APP_LOG_JSON`                    | `false`                        | 结构化日志输出为 JSON                                                 |
| `APP_ALLOWED_ORIGINS`             | `["*"]`                        | CORS 白名单，逗号分隔                                                 |
| `APP_DEFAULT_LOCALE`              | `en-US`                        | 错误消息默认语言（`en-US` / `zh-CN`）                                  |


完整列表见 `[app/core/config.py](./app/core/config.py)` 与 `[.env.example](./.env.example)`。

### 生产环境安全校验

当 `APP_ENV=production` 时，应用在**启动阶段 fail-fast**，下列任一不安全配置都会直接拒绝启动（见 `Settings._validate_production_safety`）：

- `APP_JWT_SECRET` 不能为默认值，必须是高强度随机密钥。
- `APP_ALLOWED_ORIGINS` 不能为通配符 `["*"]`，必须显式列出受信任来源。
- `APP_DB_CREATE_TABLES_ON_STARTUP` 必须为 `false`，生产通过 Alembic 迁移建表。
- `APP_DATABASE_URL` 必须使用 PostgreSQL。
- `APP_LOG_JSON` 必须为 `true`，输出 JSON 结构化日志。

开发 / 测试环境不触发该校验，保持开箱即用。OpenAPI 文档在非 `development` / `test` 环境默认隐藏。

### 切换到 PostgreSQL

```env
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app
APP_DB_CREATE_TABLES_ON_STARTUP=false
```

仓库已包含初始迁移（`alembic/versions/`），直接升级即可建表；后续模型变更用 `make revision` 自动生成新迁移：

```bash
uv run alembic upgrade head          # 应用迁移（首次即建表）
make revision m="describe change"    # 模型变更后自动生成新迁移
```

## API 示例


| 方法     | 路径                        | 说明                               |
| ------ | ------------------------- | -------------------------------- |
| `GET`  | `/api/v1/health/live`     | 存活探针（K8s liveness）               |
| `GET`  | `/api/v1/health/ready`    | 就绪探针（校验数据库连接）                    |
| `POST` | `/api/v1/users`           | 注册用户                             |
| `GET`  | `/api/v1/users`           | 分页列出用户                           |
| `GET`  | `/api/v1/users/{user_id}` | 获取用户                             |
| `POST` | `/api/v1/auth/token`      | 登录，获取 access + refresh token     |
| `POST` | `/api/v1/auth/refresh`    | 刷新令牌（轮换 refresh token）           |
| `POST` | `/api/v1/auth/logout`     | 登出当前会话（传 refresh_token）          |
| `POST` | `/api/v1/auth/logout-all` | 登出该用户全部会话（需登录）                   |
| `GET`  | `/api/v1/auth/me`         | 获取当前登录用户信息                       |


`users` 列表/详情接口需要 `users:read` 权限（见下文 RBAC）；注册（`POST /users`）保持公开以支持自助注册与引导。

### 权限（RBAC）

- 模型：`roles` / `permissions` / `user_roles` / `role_permissions`，权限码格式 `resource:action`（如 `users:read`）。
- 路由用 `Depends(RequirePermission("users:read"))` 声明所需权限：未认证 401，已认证但无权限 403（`AUTH_PERMISSION_DENIED`）。
- 启动时**幂等播种**权限目录与 `admin`（全权限）/`user`（暂无权限）两个角色（`app/auth/seed.py`），生产经迁移建表后启动即填充。
- **引导**：第一个注册的用户自动成为 `admin`，之后的用户默认 `user`。需要更多角色/分配时，扩展 `RbacRepository` 或后续加管理接口。

### 错误消息本地化（i18n）

- 错误**码**（如 `USER_NOT_FOUND`）是稳定契约，**永不翻译**；可本地化的只有 `message`。
- 领域异常携带 `message_key`，全局处理器按 `Accept-Language` 协商语言（用户偏好 → `Accept-Language` → `APP_DEFAULT_LOCALE`）后翻译消息。
- 目录在 `locales/{en-US,zh-CN}.json`；缺失翻译回退默认语言，再缺失用异常自带英文消息。

```bash
curl -H "Accept-Language: zh-CN" -X POST .../api/v1/auth/token -d '{"email":"x@e.com","password":"wrongpass"}'
# {"code":"AUTH_INVALID_CREDENTIALS","message":"邮箱或密码错误","data":null,"request_id":"..."}
```

### OpenAPI 文档标准

- 每个路由都声明 `summary` / `description` / `response_model` / `tags`，并用 `app/core/openapi.py` 的 `error_responses(...)` 复用统一的 `ErrorResponse` 错误信封。
- 受保护接口在 OpenAPI 中携带 Bearer 认证元数据；非 `development` / `test` 环境默认隐藏文档。

### 认证与会话

- access token 短期、无状态，仅校验签名与过期，不查库；refresh token 长期且服务端跟踪。
- 每次登录创建一条 `auth_sessions` 记录，**只存 refresh token 的 sha256 哈希**，不存原始 token。
- `/auth/refresh` 会**轮换** refresh token（旧的随即失效）；检测到已轮换/已撤销的 token 被复用时，撤销该用户全部会话并返回 401。
- `/auth/logout` 撤销当前会话，`/auth/logout-all` 撤销该用户全部会话（已签发的 access token 在到期前仍有效，建议保持较短有效期）。

### 后台任务与周期任务

后台队列和周期任务统一使用 Arq，依赖 Redis。API 进程只负责通过 `ArqPool` 入队；worker 进程负责消费队列和触发 `cron_jobs`。

```bash
# 本地单独启动 worker
APP_REDIS_URL=redis://localhost:6379/0 uv run arq app.worker.WorkerSettings

# 完整本地栈会同时启动 api / worker / PostgreSQL / Redis
docker compose up
```

新增普通后台任务：

1. 在 `app/worker.py` 新增 async 任务函数，首参为 `ctx: dict`。
2. 把函数加入 `WorkerSettings.functions`。
3. 在 API service/router 中注入 `queue: ArqPool` 后调用 `await queue.enqueue_job("task_name", ...)`。

新增周期任务：

1. 在 `app/worker.py` 新增 async 任务函数。
2. 同时加入 `WorkerSettings.functions` 和 `WorkerSettings.cron_jobs`。
3. 用 `arq.cron(...)` 声明计划时间，例如当前示例 `scheduled_maintenance_daily` 每天 `03:00:00` 执行。
4. 为任务函数和 cron 注册写测试，避免重命名函数后忘记更新 worker 配置。

生产环境建议将 API 与 worker 部署为两个独立进程或两个独立容器。若任务依赖数据库，也要给 worker 配置同一套 `APP_DATABASE_URL` / 迁移流程；不要在 API 进程里启动阻塞式调度器。

## 测试

测试为**真集成测试**，依赖 PostgreSQL + Redis，最大限度覆盖生产路径。

```bash
make test-up   # 启动测试依赖容器（PG + Redis）
make test      # 运行 pytest
make test-down # 停止并清理
```

测试容器通过 `docker-compose.test.yml` 与 dev 栈隔离：


| 组件         | 端口               | 数据库        | 持久化         |
| ---------- | ---------------- | ---------- | ----------- |
| PostgreSQL | `localhost:5433` | `app_test` | tmpfs（即开即清） |
| Redis      | `localhost:6380` | DB 0       | 无 RDB / AOF |


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

安装后，每次 `git commit` 会运行 **pre-commit** 中的检查（与 `.pre-commit-config.yaml` 一致：当前为 `ruff check`、`ruff format`、**mypy `app`**）。完整测试与 CI 一致请用 `make ci`（集成测试需先有 PostgreSQL + Redis，见上文「运行测试」）。

## AI 开发工作流

本项目使用 `.agents/` 作为 AI 开发规则的统一入口：

- `.agents/skills/` — 项目工作流与社区 skills
- `.agents/rules/` — 可复用项目规则
- `.agents/rules/INDEX.md` — 规则快速索引
- `.agents/requirements.md` — 当前活跃需求与决策记录
- `.agents/requirements/INDEX.md` — 需求主题索引和跳转

社区 skills 通过 `npx skills` 管理，安装时使用 `--agent codex --copy -y`
以写入 `.agents/skills/` 并更新 `skills-lock.json`。完整命令见
[.agents/README.md](./.agents/README.md)。

重要 AI 工作流和架构决策记录在 [docs/adr/](./docs/adr/)。

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

## CI/CD

完整 GitHub Actions 工作流位于 `[.github/workflows/](./.github/workflows)`：


| 工作流                                              | 触发                 | 作用                                                                                                   |
| ------------------------------------------------ | ------------------ | ---------------------------------------------------------------------------------------------------- |
| `[ci.yml](./.github/workflows/ci.yml)`           | push / PR → `main` | Ruff lint + format、mypy、pytest + 覆盖率（PG + Redis services）、Alembic 升/降级、Docker 构建验证、安全扫描（依赖漏洞、静态检查、Trivy 镜像漏洞扫描） |
| `[codeql.yml](./.github/workflows/codeql.yml)`   | push / PR → `main` + weekly | CodeQL Python 语义安全扫描（`security-extended` + `security-and-quality`） |
| `[release.yml](./.github/workflows/release.yml)` | `v*.*.*` tag 或手动   | 基于 commit 历史自动生成 Changelog 并创建 GitHub Release                                                        |


配套：

- `[.github/dependabot.yml](./.github/dependabot.yml)` — 每周自动升级 uv / GitHub Actions / Dockerfile 依赖
- `[.dockerignore](./.dockerignore)` — 最小化镜像构建上下文
- `[docs/release-chain.md](./docs/release-chain.md)` — 发布链路、镜像版本、部署与回滚方案

### 首次启用前的准备

1. 仓库 **Settings → Actions → General → Workflow permissions** 保持默认即可（当前流程不涉及镜像推送）。
2. （可选）在 **Settings → Secrets and variables → Actions** 添加 `CODECOV_TOKEN` 启用覆盖率上传。

### 本地复现 CI

```bash
make ci           # 等价于 lint + format-check + typecheck + cov
docker build .    # 验证镜像构建
```

## 路线图

- OAuth2 / OIDC 第三方登录示例
- 细粒度权限（RBAC / Casbin）示例
- OpenTelemetry 链路追踪
- 多租户 / 多环境配置示例
- WebSocket 示例
- 事件驱动（domain events / outbox）示例

欢迎通过 [Issues](https://github.com/gggjjto/fastapi-template/issues) 讨论新方向。

## 进阶可选项

以下能力默认不启用，保持模板轻量；当项目进入团队协作或生产化阶段再按需开启：

- Docker 镜像自动发布（GHCR / 自建 registry）
- SBOM 与构建 attestation

## 贡献

欢迎 Issue 与 Pull Request！

贡献细则见 `[CONTRIBUTING.md](./CONTRIBUTING.md)`，安全问题提交流程见 `[SECURITY.md](./SECURITY.md)`。

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/awesome`
3. 本地通过所有检查：`make ci`
4. 提交（推荐 [Conventional Commits](https://www.conventionalcommits.org/)）：`git commit -m "feat: add awesome"`
5. 推送并发起 PR

提交前请确保：

- `make lint` 通过
- `make format` 已运行
- `make test` 通过（需先 `make test-up`）
- 新代码补充了对应测试

## 许可证

本项目基于 [MIT License](./LICENSE) 开源 —— 可自由用于商业与个人项目。

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) — 项目的基石
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) — 领域化目录约定参考
- [astral-sh/uv](https://github.com/astral-sh/uv) 与 [astral-sh/ruff](https://github.com/astral-sh/ruff) — 现代 Python 工具链
- 所有依赖开源库的作者 — 没有你们就没有这个模板

---

如果这个模板对你有帮助，欢迎给一个 [Star](https://github.com/gggjjto/fastapi-template/stargazers)
