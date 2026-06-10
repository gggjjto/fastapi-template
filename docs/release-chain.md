# 发布链路方案

本文说明本 FastAPI 模板推荐的发布链路：代码从 PR 合并后，如何变成可追踪、可部署、可回滚的生产制品。

## 目标

- 让发布可重复，减少手工操作。
- 在制品发布前保留质量和安全门禁。
- 产出不可变、可追踪的 Docker 镜像。
- 让回滚成为常规操作，而不是临时补救。
- 保持模板默认轻量，同时给生产部署留下清晰路径。

## 当前状态

项目已经具备大部分发布前基础设施：

- PR CI 已包含 lint、format check、mypy、测试、Alembic migration 验证、Docker build 验证和安全检查。
- Dependabot 会持续暴露 Python、GitHub Actions、Dockerfile 依赖更新。
- `release.yml` 已能基于 `v*.*.*` tag 创建 GitHub Release。
- Dockerfile 已能构建生产运行镜像，但当前 CI 只验证构建，不发布镜像。

还缺的生产发布能力：

- 将 Docker 镜像发布到 registry。开源侧可用 GHCR；国内服务器部署应同步到国内可稳定拉取的 registry。
- 定义镜像 tag 策略。
- 在 release 中记录 image digest、source commit 等元数据。
- 明确部署和回滚流程。
- 后续可选：生成 SBOM、构建 provenance、镜像签名。

## 目标流程

```text
Pull Request
  -> CI 门禁通过
  -> Merge to main
  -> main 分支 CI 门禁通过
  -> 创建版本 tag，例如 v0.2.0
  -> Release workflow 构建 Docker 镜像
  -> 推送镜像到 GHCR 和/或自建 registry
  -> 创建 GitHub Release，包含 changelog、镜像 tag、digest、迁移说明
  -> 国内服务器使用自建 registry 的指定 image digest 部署
  -> 观察 health check、日志、错误监控
  -> 如有问题，回滚到上一个 digest
```

## 版本策略

使用 SemVer 风格 tag：

- `v0.1.1`：bug fix 或安全修复。
- `v0.2.0`：向后兼容的新功能。
- `v1.0.0` 及以上：公共 API 进入稳定阶段。
- `v0.2.0-rc.1`：需要预发布验证时使用 release candidate。

Git tag 是 release 身份。Docker tag 是人类易读的指针，真正生产部署优先使用不可变的 image digest。

## Docker 镜像 Tag

发布镜像时，同一个镜像建议打多个 tag：

- `ghcr.io/<owner>/fastapi-template:v0.2.0`
- `ghcr.io/<owner>/fastapi-template:0.2`
- `ghcr.io/<owner>/fastapi-template:sha-<short_sha>`
- `ghcr.io/<owner>/fastapi-template:latest` 仅用于稳定版本，不用于 prerelease。

生产部署优先使用 digest：

```text
ghcr.io/<owner>/fastapi-template@sha256:<digest>
```

tag 方便人看；digest 更适合生产，因为 digest 不会漂移。

## 国内服务器镜像策略

如果生产服务器在中国国内，不建议把运行时部署强依赖放在 GHCR 或 Docker Hub 上。默认推荐采用“自建 registry 优先”的策略，避免绑定任何国内云服务商。

- GitHub Release 仍可发布到 GHCR，作为开源分发和海外环境默认来源。
- 国内生产部署使用自建 Harbor、Docker Registry v2，或团队内网已有的镜像仓库。
- release workflow 构建一次镜像后，推送同一镜像到多个 registry。
- release note 同时记录 GHCR digest 和自建 registry digest。
- 国内部署文档和服务器配置默认使用自建 registry 地址。

示例：

```text
# 海外 / 开源分发
ghcr.io/<owner>/fastapi-template:v0.2.0
ghcr.io/<owner>/fastapi-template@sha256:<digest>

# 国内生产部署，示例为自建 Harbor
registry.example.internal/backend/fastapi-template:v0.2.0
registry.example.internal/backend/fastapi-template@sha256:<digest>
```

国内部署优先级建议：

1. **首选：自建 Harbor / Docker Registry v2 发布应用镜像**。服务器只拉取内网或国内可达的自建 registry，稳定性最好。
2. **可选：registry mirror 作为缓存层**。适合多项目、多服务器统一管理基础镜像和应用镜像。
3. **兜底：离线导入镜像**。在可访问外网的机器执行 `docker save`，上传到服务器后 `docker load`，适合临时救急，不适合作为长期发布链路。

基础镜像也要考虑国内可用性：

- `python:3.12-slim`、`postgres:16-alpine`、`redis:7-alpine` 默认来自 Docker Hub，国内服务器直接拉取可能失败。
- CI 构建可以继续在 GitHub-hosted runner 上使用 Docker Hub。
- 生产服务器不需要拉取这些基础镜像，只需要拉取已经构建好的应用镜像。
- 如果需要在国内服务器上构建镜像，应使用自建 registry 缓存基础镜像，或提前把可信基础镜像同步进内网 registry。

不要依赖非官方、不可信的公共镜像加速源来拉生产镜像。生产镜像来源应可审计、可控，并尽量固定 digest。

## 发布前门禁

release workflow 只有在以下门禁都通过后才应发布制品：

- Ruff lint 和 format check。
- mypy 类型检查。
- pytest 集成测试。
- Alembic upgrade / downgrade 验证。
- Docker 镜像构建与 smoke test。
- 依赖漏洞与静态安全检查。
- Trivy 镜像扫描，阻断可修复的 HIGH / CRITICAL 漏洞。
- CodeQL Python 安全扫描。

任一门禁失败，不应发布 Docker 镜像。

## GitHub Release 内容

每个 GitHub Release 应包含：

- 版本 tag。
- 相对上一个 tag 的 changelog。
- source commit SHA。
- Docker image tags。
- Docker image digest。
- 数据库迁移说明：
  - 是否包含 migration。
  - 是否容易回滚。
  - 是否需要手工数据迁移。
- 已知风险或运维注意事项。

## 部署模型

构建和部署建议分离：

- release workflow 负责构建和发布制品。
- 部署 workflow、托管平台或人工操作负责选择何时部署某个已发布制品。

小项目可以先从手工部署开始：

1. 创建 tag：`vX.Y.Z`。
2. 等待 release workflow 发布镜像。
3. 将目标环境更新到本次 release 的 image digest。
4. 执行 Alembic migration。
5. 重启 API 和 worker 进程。
6. 检查 `/api/v1/health/live` 和 `/api/v1/health/ready`。

项目变大后再加环境级自动化：

- `deploy-staging.yml`：稳定 release 后自动部署 staging。
- `deploy-production.yml`：通过 GitHub Environment approval 后部署 production。

## 数据库迁移顺序

生产部署推荐顺序：

1. 如果 release 包含高风险 schema 或数据变更，先备份数据库。
2. 尽量先部署兼容旧 schema 的代码。
3. 执行 `alembic upgrade head`。
4. 重启 API 和 worker 进程。
5. 验证 readiness 和核心业务路径。

优先写向后兼容 migration：

- 先添加 nullable column，再逐步要求必填。
- 先 backfill 数据，再加约束。
- 旧代码完全下线前，不急着删除旧列。
- 避免在同一个 release 中同时做破坏性 migration 和依赖该破坏性变更的新代码。

## 回滚策略

发布前就要想好回滚。

应用回滚：

```text
部署上一个已知可用 image digest
重启 API 和 worker
验证 health check 与日志
```

数据库回滚：

- 如果 migration 向后兼容，可以部署旧镜像并保留新 schema。
- 如果 migration 不向后兼容，发布前必须准备并测试 Alembic downgrade。
- 对破坏性 migration，除非有测试过的数据恢复方案，否则通常优先 forward fix。

release note 里应明确写出本次 release 的回滚预期。

## Secrets 与权限

发布到 GHCR 时，release workflow 通常需要：

- `contents: read`
- `packages: write`
- 后续如果加入 provenance / keyless signing，再使用 `id-token: write`

不要把长期 registry 密码放进仓库。发布 GHCR 镜像时优先使用 GitHub 内置的 `GITHUB_TOKEN`。

发布到自建 registry 时，把 registry 地址、用户名、密码或临时访问凭证放在 GitHub Actions Secrets 中，例如：

- `PRIVATE_REGISTRY`
- `PRIVATE_REGISTRY_NAMESPACE`
- `PRIVATE_REGISTRY_USERNAME`
- `PRIVATE_REGISTRY_PASSWORD`

如果 registry 支持短期 token，优先使用短期凭证，减少长期密码暴露面。否则为 CI 单独创建最小权限账号，只允许 push 指定 namespace。

运行时 secrets，例如 `APP_JWT_SECRET`、数据库凭证、Redis 凭证、Sentry DSN，必须由部署平台注入，不能烘焙进镜像。

## 分阶段落地计划

### 阶段一：发布镜像

- 扩展 `release.yml`，在 `v*.*.*` tag 上构建 Docker 镜像。
- 推送到 GHCR；如果配置了自建 registry secrets，同时推送到自建 registry。
- 将 image tags、GHCR digest、自建 registry digest 写入 GitHub Release body。
- 部署仍保持手工。

### 阶段二：发布加固

- 生成 SBOM。
- 增加 build provenance attestation。
- 可选：签名镜像。
- 文档化如何校验 image digest 和 provenance。

### 阶段三：部署自动化

- 增加 staging release 自动部署。
- 增加 production 手工 approval 部署。
- 增加 post-deploy smoke check。
- 增加回滚 workflow，用于重新部署上一个 digest。

## 当前非目标

- 默认不加入 Kubernetes 专用 manifests。
- 默认不绑定具体云厂商流水线。
- 不从每次 merge to `main` 自动部署 production。
- 在没有多环境协作前，不引入复杂 release train。

## 推荐下一步 PR

下一步最实际的是先做阶段一：

- 在 `release.yml` 中构建镜像，并支持推送到 GHCR 与可选自建 registry。
- 发布 `vX.Y.Z`、`X.Y`、`sha-<short_sha>`，稳定版本额外发布 `latest`。
- 将推送后的 image digest 写入 GitHub Release。
- 保持部署手工，但文档化操作步骤。
