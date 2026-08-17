---
doc_type: convention
status: active
authority: normative
scope: fastapi-backend
last_reviewed: 2026-08-17
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
| POST | `/users` | 无 | 创建普通用户，不授予平台管理员权限 |
| GET | `/users` | `users:read` | 分页用户列表 |
| GET | `/users/{user_id}` | `users:read` | 查询用户 |
| GET/POST | `/tenants` | 登录用户 / `platform_admin` | 查看所属租户 / 创建租户 |
| GET/PATCH | `/tenants/{tenant_id}` | 租户成员 / owner | 查询或更新租户 |
| GET | `/tenants/{tenant_id}/members` | 租户成员 | 查看成员 |
| POST | `/tenants/{tenant_id}/invitations` | owner、admin | 创建成员邀请 |
| POST | `/tenant-invitations/accept` | 登录或新用户 | 接受请求体中的单次邀请 token |
| GET/POST | `/tenants/{tenant_id}/crawler/targets` | 租户成员 / owner、admin | 管理采集目标 |
| GET | `/tenants/{tenant_id}/crawler/jobs` | 租户成员 | 查询采集任务 |
| POST | `/tenants/{tenant_id}/crawler/targets/{target_id}/run` | 租户成员 | 手动触发任务 |
| POST | `/tenants/{tenant_id}/crawler/jobs/{job_id}/cancel` | owner、admin | 取消任务 |
| POST | `/tenants/{tenant_id}/crawler/jobs/{job_id}/retry` | owner、admin | 从失败或取消任务创建新任务 |

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
- 全局 RBAC 使用 role、permission、user-role 和 role-permission 表；`platform_admin` 管理全部租户。
- 租户内角色固定为 `owner`、`admin`、`member`，由 membership 保存。
- 首个平台管理员只能通过显式 bootstrap CLI 创建，普通注册永远不会自动提权。
- 邀请 token 只保存 SHA-256 哈希、单次使用并默认 72 小时过期；接受时必须匹配邮箱。
- 所有租户资源查询必须同时包含 `tenant_id`，跨租户资源统一表现为不存在。

当前不提供动态租户角色定义或租户硬删除。

## 配置

配置由 `apps/api/app/core/config.py` 的 `Settings` 定义，环境变量使用 `APP_` 前缀。完整样例见 `apps/api/.env.example`。

生产环境启动会拒绝：

- 默认 JWT secret；
- `APP_ALLOWED_ORIGINS=*`；
- `APP_DB_CREATE_TABLES_ON_STARTUP=true`；
- 非 PostgreSQL 数据库；
- 非 JSON 日志。

Redis 与 Sentry 均可通过空配置关闭。限流在 Redis 已配置时使用 Redis，否则使用进程内存。Hatchet token 只在 worker、dispatcher 或 scheduler 运行时需要。

## 数据与迁移

- 使用异步 SQLAlchemy；通过 `DBSession` 注入 session。
- Schema 变更必须提交 Alembic migration。
- 开发可启用 `create_all`；生产只能运行 Alembic。
- 迁移必须通过 upgrade、`alembic check`、单步 downgrade 和重新 upgrade。

## Crawler 安全边界

Crawler handler 只能放在 `app/crawler/handlers/`。Runner 统一管理持久化、重试、并发、限速和网络策略；Hatchet payload 只携带 `crawl_job_id`，runner 从数据库加载租户与 target。

安全 HTTP client 会拒绝非 HTTP(S)、私有/回环/链路本地等地址、跨 host 重定向、过多重定向和超大响应体。`http_snapshot` 只持久化文本正文的前 256 KiB；二进制只保存元数据和 SHA-256。它不是通用 HTTP client，不应绕过。
