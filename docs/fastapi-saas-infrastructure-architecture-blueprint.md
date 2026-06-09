# FastAPI SaaS 工程基建与应用架构蓝图

## 1. 文档目的

本文档用于沉淀当前项目的长期工程基建与应用架构蓝图，作为后续 AI agent 执行实现、拆分任务、评审架构决策的上层依据。

本文档关注：

- 长期维护
- 团队协作
- 扩展性
- 安全性
- 可观测性
- SaaS 化演进能力

本文档不直接替代具体需求文档和技术设计文档。具体需求与执行细节见：

- `docs/engineering-foundation-requirements.md`
- `docs/engineering-foundation-design.md`

## 2. 当前项目定位

当前项目是一个质量较高的 FastAPI 后端模板，已经具备真实业务项目需要的基础能力：

- 按领域组织的代码结构。
- FastAPI + Pydantic v2。
- SQLAlchemy async + Alembic。
- JWT access / refresh token。
- Redis 缓存与 Arq 后台任务队列基础。
- 统一响应体。
- 全局 HTTP 与参数校验异常处理。
- 结构化日志与 Request ID。
- Sentry 错误追踪。
- slowapi 限流。
- Docker 与 Docker Compose。
- GitHub Actions CI。
- Ruff、mypy、pytest、coverage。
- PostgreSQL + Redis 集成测试。
- Dependabot 与基础安全扫描。

因此，当前项目不应再被视为一个空脚手架，而应被视为一个“可继续生产化打磨的模块化单体后端底座”。

## 3. 架构总原则

### 3.1 先模块化单体，后服务拆分

当前阶段建议保持模块化单体：

```text
FastAPI application
  auth domain
  users domain
  health domain
  core infrastructure
  db infrastructure
  worker entrypoint
```

不建议过早拆成微服务。只有当以下条件明确出现时，再考虑拆分：

- 独立团队拥有独立领域。
- 某个领域需要独立扩缩容。
- 某个领域有明显不同的发布节奏。
- 某个领域有独立数据隔离或合规要求。
- 单体内部边界已经稳定，拆分成本可控。

### 3.2 平台能力先于业务堆叠

后续不要优先继续堆业务 endpoint，而应先补齐平台能力：

- 错误码体系。
- 全局领域异常处理。
- 配置安全校验。
- Alembic 首版迁移。
- JWT session 治理。
- RBAC。
- OpenAPI 规范。
- 国际化错误消息。
- 审计日志。
- 可观测性。

这些能力会影响所有后续业务域。如果后期再补，会产生大量返工。

### 3.3 所有生产变更必须可观测、可回滚、可审计

生产级系统不是“能跑起来”即可，而是要满足：

- 出问题能定位。
- 出错后能回滚。
- 谁改了什么能审计。
- 线上状态能度量。
- 关键风险能提前告警。

## 4. 目标运行架构

目标架构分为四层。

### 4.1 边缘与接入层

职责：

- 稳定接入。
- TLS 终止。
- 流量保护。
- 协议治理。
- 外部 API 入口统一。

建议能力：

- CDN。
- WAF。
- API Gateway。
- TLS / HSTS。
- CORS allowlist。
- IP / 用户 / 租户维度限流。
- 请求大小限制。
- 基础 Bot 防护。

当前项目已有：

- FastAPI CORS middleware。
- slowapi 基础限流。

待补齐：

- 生产 CORS 安全校验。
- 分布式限流。
- 网关级统一策略。
- WAF / CDN / TLS 部署设计。

### 4.2 应用服务层

职责：

- 承载领域业务。
- 认证鉴权。
- API 契约。
- 后台任务入口。
- 横切能力接入。

建议能力：

- Domain-oriented 模块。
- Thin router。
- Service 承载业务规则。
- Repository 承载数据访问。
- 统一异常与错误码。
- JWT AuthN。
- RBAC AuthZ。
- API versioning。
- Background worker。
- OpenAPI 文档规范。

当前项目已有：

- `auth`、`users`、`health` 领域。
- `router/service/repository/model/schema` 分层。
- JWT 基础鉴权。
- Arq worker 基础。
- `/api/v1` 路由前缀。

待补齐：

- 用户 API 权限边界。
- RBAC。
- Refresh token session。
- OpenAPI 统一规范。
- 领域异常全局处理。
- 后台任务幂等与死信策略。

### 4.3 平台与数据层

职责：

- 可靠存储。
- 缓存。
- 异步任务。
- 数据迁移。
- 备份恢复。

建议能力：

- PostgreSQL。
- Redis。
- Arq queue。
- Alembic migration。
- Object storage。
- Backup and restore。
- 数据生命周期管理。
- 慢查询治理。
- 连接池治理。

当前项目已有：

- SQLAlchemy async。
- Alembic 配置。
- PostgreSQL 测试栈。
- Redis 连接管理。
- RedisCache。
- Arq。

待补齐：

- Alembic 首版 migration。
- 生产禁用 `create_all`。
- 迁移规范。
- 备份恢复演练。
- 队列积压监控。
- 缓存失效策略。

### 4.4 治理与观测层

职责：

- 质量门禁。
- 发布治理。
- 安全扫描。
- 可观测性。
- 事故响应。
- 团队协作规范。

建议能力：

- CI/CD。
- IaC。
- Secret Manager。
- OpenTelemetry。
- Metrics。
- SLO。
- Alerts。
- Audit logs。
- ADR。
- CODEOWNERS。
- Runbook。

当前项目已有：

- GitHub Actions CI。
- Ruff / mypy / pytest。
- pip-audit / bandit。
- Docker build smoke test。
- structlog。
- Request ID。
- Sentry。

待补齐：

- 镜像发布。
- SBOM。
- 容器扫描。
- 镜像签名。
- IaC。
- K8s / Helm / Kustomize。
- OpenTelemetry traces。
- Prometheus metrics。
- SLO 与告警分级。
- 审计日志。
- 运行手册。

## 5. 当前代码级 P0 风险

这些是从当前代码和配置中可以直接看到的生产化阻塞点，应优先排进近期技术债迭代。

### 5.1 Alembic 首版迁移缺失

现状：

- Alembic 框架已接入。
- `alembic/versions/` 尚无首版 migration。
- 当前仍存在开发期 `create_all` 路径。

风险：

- 生产 schema 演进无可审计历史。
- 后续模型变化无法可靠回滚或审查。

建议：

- 立即补齐当前 schema 的首版 Alembic migration。
- 生产环境强制 `APP_DB_CREATE_TABLES_ON_STARTUP=false`。
- CI 持续验证 `alembic upgrade head`。

### 5.2 用户 API 鉴权边界偏宽

现状：

- `/auth/me` 需要登录。
- 用户创建、列表、详情接口目前仍偏示例化，权限边界不完整。

风险：

- 用户数据泄露。
- 管理接口与普通用户接口混用。
- 后续加权限时改动面变大。

建议：

- 明确公开注册接口与受保护用户接口。
- `list users` 至少需要管理员或 `users:read` 权限。
- `get user` 应区分“读取自己”和“读取任意用户”。

### 5.3 Refresh token 无状态

现状：

- 已有 access / refresh token。
- refresh token 没有服务端 session 记录。
- 不支持 revoke、rotation、logout、设备管理。

风险：

- token 泄露后难以及时失效。
- 用户无法主动退出全部设备。
- 无法检测 refresh token 复用。

建议：

- 增加 `auth_sessions` 表。
- refresh token 只存 hash。
- 每次 refresh 轮换 token。
- 支持 logout 和 revoke all sessions。

### 5.4 限流非分布式

现状：

- slowapi 基础限流存在。
- 默认内存存储在多副本下不一致。

风险：

- 水平扩容后限流失效或不准确。
- 登录爆破防护能力不足。

建议：

- 接入 Redis backend。
- 或将主要限流上移到 API Gateway。
- 区分 IP、用户、租户、接口维度限流。

### 5.5 Worker 未形成生产部署单元

现状：

- Arq 基建存在。
- `docker-compose.yml` 中 worker 默认注释。
- 业务任务可靠性策略尚未固化。

风险：

- 后台任务在生产中容易成为黑盒。
- 重试、幂等、死信、积压缺少治理。

建议：

- worker 作为独立部署单元。
- 所有任务必须具备幂等键。
- 增加任务状态、失败重试、死信处理和队列积压告警。

### 5.6 业务缓存策略未落地

现状：

- `RedisCache` 已有封装。
- 示例业务域尚未接入缓存。

风险：

- 后续业务自行使用 Redis，容易形成不一致策略。
- 缓存穿透、击穿、雪崩没有统一规范。

建议：

- 先定义缓存使用原则。
- 只在读多写少且一致性要求明确的场景启用。
- 明确 TTL、key 命名、失效策略。

### 5.7 DomainError 未全局统一处理

现状：

- 已有 `DomainError` 基类。
- 部分领域异常仍需要 router 手动转换。

风险：

- 错误响应不一致。
- 新业务域容易重复 try/except。
- OpenAPI 错误响应难统一。

建议：

- `DomainError` 携带 `code`、`message`、`status_code`。
- 全局 handler 统一转换。
- router 不再手写领域异常转换。

### 5.8 审计与软删除缺失

现状：

- 用户模型没有软删除和审计字段。
- 系统没有审计日志表。

风险：

- 难以满足 SaaS 客服、合规、追责和数据恢复要求。

建议：

- 引入 `created_at`、`updated_at`、`deleted_at`。
- 关键操作写入 audit log。
- 审计日志记录 actor、action、resource、tenant、request_id。

## 6. 工程基础设施能力域

### 6.1 环境与部署

目标：

- 本地、测试、预发、生产清晰隔离。

建议：

- 本地使用 Docker Compose。
- 测试使用 `docker-compose.test.yml`。
- 生产使用 Kubernetes。
- 环境差异使用 Helm 或 Kustomize 管理。

### 6.2 IaC

目标：

- 基础设施可审计、可复现。

建议：

- 使用 Terraform 或 OpenTofu。
- 管理 VPC、数据库、Redis、对象存储、DNS、证书、告警。
- 禁止手工改生产资源。

### 6.3 CI/CD

目标：

- 每次变更可验证、可发布、可回滚。

建议：

- 保留当前 lint、format、mypy、test、migration、docker build。
- 增加 Trivy 或 Grype 容器扫描。
- 增加 SBOM。
- 增加镜像签名。
- 增加 GHCR 或云厂商镜像仓库推送。
- 增加 staging 自动部署。
- production 采用手动审批或变更窗口。

### 6.4 配置与密钥

目标：

- 配置集中、密钥安全、生产启动失败优于带病运行。

建议：

- 保持 `APP_` 前缀。
- 本地 `.env`。
- 生产使用 Secret Manager 或 K8s Secret。
- `Settings` 中增加生产安全校验。
- JWT secret 支持轮换策略。

### 6.5 数据库治理

目标：

- schema 演进安全，数据可恢复。

建议：

- 使用 Alembic。
- 采用 expand-contract 迁移。
- 定期备份恢复演练。
- 监控慢查询。
- 规划连接池大小。
- 中长期准备读写分离。

### 6.6 可观测性

目标：

- 线上问题能快速定位，系统健康能被量化。

建议：

- Logs：structlog JSON。
- Metrics：Prometheus。
- Traces：OpenTelemetry。
- Errors：Sentry。
- SLO：延迟、错误率、可用性。
- Alerts：按严重级别分层。

关键指标：

- API QPS。
- HTTP 4xx / 5xx。
- p50 / p95 / p99 latency。
- DB pool usage。
- DB query latency。
- Redis latency。
- Arq queue depth。
- Worker failure count。

### 6.7 安全

目标：

- 降低认证、授权、供应链和数据泄露风险。

建议：

- JWT session rotation。
- RBAC。
- 最小权限。
- 审计日志。
- 依赖扫描。
- SAST。
- 容器扫描。
- Secret scanning。
- WAF。
- 登录失败限流。
- OpenAPI 生产隐藏或保护。

### 6.8 协作治理

目标：

- 团队多人协作时保持架构一致性。

建议：

- ADR。
- CODEOWNERS。
- PR template。
- 架构变更 checklist。
- 运行手册。
- 事故复盘模板。
- 文档维护规则。

### 6.9 SaaS 平台能力

目标：

- 为多租户和商业化能力预留稳定扩展路径。

建议：

- organization / tenant。
- organization members。
- roles / permissions。
- audit logs。
- quota。
- subscription。
- webhook。
- background jobs。
- event outbox。

### 6.10 成本与容量

目标：

- 支持长期运营和资源优化。

建议：

- Kubernetes requests / limits。
- HPA。
- 数据库容量规划。
- Redis 内存策略。
- 队列积压告警。
- 成本标签。
- 按环境和服务拆分成本报表。

## 7. 应用架构原则

### 7.1 领域边界

继续保持 domain-oriented 结构：

```text
app/<domain>/
  router.py
  service.py
  repository.py
  models.py
  schemas.py
  dependencies.py
  exceptions.py
  constants.py
```

原则：

- 一个业务域的主要变更应尽量集中在一个目录中。
- 不按技术层横向拆成 `routers/ services/ repositories/`。
- `core` 只放跨领域基础设施。

### 7.2 Router

职责：

- HTTP 参数解析。
- FastAPI dependency 声明。
- response model 声明。
- OpenAPI metadata。
- 调用 service。

不应承担：

- 业务规则。
- 复杂权限判断。
- 数据库查询。
- 手写异常转换。

### 7.3 Service

职责：

- 业务规则。
- 事务边界。
- 幂等语义。
- 领域异常。
- 调用 repository。

原则：

- Service 抛 `DomainError` 子类。
- Service 不依赖 FastAPI request/response。

### 7.4 Repository

职责：

- 数据访问。
- 查询封装。
- 持久化。

原则：

- Repository 不应泄露 HTTP 概念。
- Repository 不做权限判断，除非是租户作用域过滤这类数据安全 invariant。

### 7.5 认证与授权

认证：

- JWT 证明“你是谁”。

授权：

- RBAC / policy 判断“你能做什么”。

原则：

- Router 声明权限需求。
- Dependency 执行权限判断。
- Service 执行资源级业务校验。

### 7.6 多租户

未来 SaaS 化时，所有核心业务表应引入：

```text
tenant_id / organization_id
```

原则：

- 查询默认带租户作用域。
- 后台任务必须携带租户上下文。
- 日志必须能记录租户上下文。
- 审计日志必须包含租户信息。

### 7.7 异步任务

原则：

- 任务参数只传稳定 ID。
- Worker 内重新加载状态。
- 任务必须幂等。
- 失败必须可重试。
- 不可恢复失败进入死信。
- 队列积压必须告警。

### 7.8 API 契约

原则：

- 公共 API 使用版本化路径。
- OpenAPI 是契约，不只是自动页面。
- 错误码稳定。
- 字段删除需要弃用窗口。
- 重要 API 做契约测试或 schema snapshot。

## 8. 推荐落地路线

### 第 1 阶段：生产就绪底座

目标：

- 让模板具备生产默认安全性。

交付：

- 错误码体系。
- 全局 `DomainError`。
- 响应体 request_id。
- Alembic 首版迁移。
- 生产配置强校验。
- OpenAPI 基础规范。

### 第 2 阶段：安全与权限

目标：

- 补齐用户鉴权与权限边界。

交付：

- JWT session 表。
- Refresh token rotation。
- Logout / revoke。
- RBAC 模型。
- `RequirePermission`。
- 用户 API 权限保护。

### 第 3 阶段：SaaS 核心平台

目标：

- 为多租户产品做准备。

交付：

- organization / tenant 模型。
- tenant-scoped RBAC。
- audit logs。
- quota 基础。
- webhook 基础。
- 后台任务可靠性治理。

### 第 4 阶段：规模化治理

目标：

- 支持更高并发、更多团队、更稳定发布。

交付：

- OpenTelemetry。
- Prometheus metrics。
- SLO / alert。
- 灰度发布。
- 自动扩缩容。
- 备份恢复演练。
- 成本归因。

### 第 5 阶段：组织级工程效能

目标：

- 将工程实践标准化。

交付：

- ADR。
- CODEOWNERS。
- 运行手册。
- 事故复盘模板。
- 架构守护规则。
- 开发者文档入口。
- 领域脚手架规范。

## 9. 架构决策原则

后续 AI 或工程师执行时，应遵循以下决策原则：

- 先固化单体模块边界，再考虑拆服务。
- 所有生产变更必须可回滚、可观测、可审计。
- 安全、租户隔离和数据迁移属于基础能力，不作为后期补丁。
- 平台能力应沉淀为内部 API 或 dependency，不复制到每个业务 router。
- 不为了“架构完整”引入暂时用不上的重型组件。
- 不把业务错误消息当作程序判断依据，程序只依赖错误码。
- 不把权限判断散落在业务代码中。
- 不把密钥、token、密码、cookie 写入日志。
- 不绕过 Alembic 修改生产 schema。

## 10. 后续 AI 执行建议

后续让 AI 执行时，建议按以下方式发起任务：

```text
请阅读：
- docs/fastapi-saas-infrastructure-architecture-blueprint.md
- docs/engineering-foundation-requirements.md
- docs/engineering-foundation-design.md

然后只实现 Phase 1：错误码体系、DomainError 全局处理、响应体 request_id 支持。
要求：
- 保持 domain-oriented 结构。
- 添加测试。
- 不引入无关重构。
- 不修改 Alembic/RBAC/JWT session，除非 Phase 1 必须。
```

每个阶段单独执行、单独测试、单独评审。不要一次性让 AI 同时实现所有阶段。
