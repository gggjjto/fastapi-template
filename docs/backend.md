---
doc_type: convention
status: active
authority: normative
scope: fastapi-backend
last_reviewed: 2026-08-12
---

# 后端契约

## 对外 API

所有业务路由位于 `APP_API_V1_PREFIX`，默认 `/api/v1`。

| 方法 | 路径 | 认证/权限 | 用途 |
| --- | --- | --- | --- |
| GET | `/health/live` | 无 | 进程存活 |
| GET | `/health/ready` | 无 | PostgreSQL 与可选 Redis 就绪 |
| POST | `/auth/token` | 无；10/minute | 登录并创建服务端 refresh session |
| POST | `/auth/refresh` | refresh token；20/minute | 轮换 access/refresh token |
| POST | `/auth/logout` | refresh token | 幂等撤销当前 session |
| POST | `/auth/logout-all` | access token | 撤销当前用户全部 refresh sessions |
| GET | `/auth/me` | access token | 当前用户 |
| POST | `/users` | 无 | 创建用户；首个用户成为 admin |
| GET | `/users` | `users:read` | 分页用户列表 |
| GET | `/users/{user_id}` | `users:read` | 查询用户 |

development 和 test 环境的 OpenAPI 默认在 `/docs`；staging 与 production 会关闭 OpenAPI URL。

## 响应与错误

DTO 继承 `CustomModel`，列表返回 `Page[T]`。HTTP 响应使用统一 envelope：

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "..."
}
```

- 成功响应通过 `ApiResponse.ok(...)` 创建。
- 领域异常由全局 handler 转换，router 不重复 `try/except`。
- 业务错误码稳定且不翻译；错误消息按 `Accept-Language` 支持 `en-US` 与 `zh-CN`。
- 未知异常不得向客户端泄漏堆栈。
- 每个请求返回或生成 request ID，并进入结构化日志上下文。

## 认证与权限

- 密码使用 bcrypt；输入上限是 72 个 UTF-8 字节。
- Access token 和 refresh token 类型不可混用。
- Refresh token 绑定 `auth_sessions`，数据库只保存 SHA-256 哈希。
- 每次 refresh 都轮换 token；旧 token 复用会撤销该用户全部 sessions。
- RBAC 使用 role、permission、user-role 和 role-permission 表。
- 启动时幂等播种权限目录和默认 `admin`、`user` 角色。

当前没有用户更新/删除、角色管理或权限分配 HTTP API。

## 配置

配置由 `apps/api/app/core/config.py` 的 `Settings` 定义，环境变量使用 `APP_` 前缀。完整样例见 `apps/api/.env.example`。

生产环境启动会拒绝：

- 默认 JWT secret；
- `APP_ALLOWED_ORIGINS=*`；
- `APP_DB_CREATE_TABLES_ON_STARTUP=true`；
- 非 PostgreSQL 数据库；
- 非 JSON 日志。

Redis 与 Sentry 均可通过空配置关闭。Hatchet token 只在 worker 或 dispatcher 运行时需要。

## 数据与迁移

- 使用异步 SQLAlchemy；通过 `DBSession` 注入 session。
- Schema 变更必须提交 Alembic migration。
- 开发可启用 `create_all`；生产只能运行 Alembic。
- 迁移必须至少通过 upgrade；CI 同时验证 downgrade 到 base。

## Crawler 安全边界

Crawler handler 只能放在 `app/crawler/handlers/`。Runner 统一管理持久化、重试、并发、限速和网络策略。

安全 HTTP client 会拒绝非 HTTP(S)、私有/回环/链路本地等地址、跨 host 重定向、过多重定向和超大响应体。它不是通用 HTTP client，不应绕过。
