---
description: 完整功能开发流程：确定需求 → 写代码 → 编写测试 → 代码检查 → 提交 commit。开始任何新功能或改动时使用。
disable-model-invocation: true
---

# Feature Workflow

从需求确认到 commit 的完整开发流程。每个阶段必须完成后再进入下一阶段。

---

## 阶段一：确定需求

在写任何代码之前，确认以下内容已明确：

- **操作目标**：新建域、新增端点、修改现有功能，还是修 bug？
- **数据模型**：涉及哪些字段？类型和校验约束？是否需要数据库迁移？
- **认证要求**：需要 `CurrentUser`？还是公开端点？
- **错误场景**：哪些情况应该返回错误？对应 HTTP 状态码？
- **成功响应**：返回什么数据结构？

有任何不清楚的地方，先提问，不要开始写代码。

---

## 阶段二：写代码

1. 找到最近的现有域，镜像其模式。
2. 按这个顺序修改文件：
   ```
   schemas.py → models.py → repository.py → service.py → dependencies.py → router.py
   ```
3. 遵循 `.claude/rules/fastapi-best-practices.md`：
   - router 只做 HTTP 适配，返回 `ApiResponse.ok(...)`
   - 业务逻辑放在 service，数据库查询放在 repository
   - 每个路由装饰器必须有 `summary`、`description`、`response_model`
4. 如果模型变了：
   - 在 `app/db/session.py` 和 `alembic/env.py` 导入新模型
   - 运行 `make revision m="描述"` 生成迁移，不要手写迁移文件

---

## 阶段三：编写测试

使用 `test-writer` agent 编写或审查集成测试。

测试要覆盖：
- 成功路径（正常响应）
- 校验错误（422）
- 资源不存在（404）
- 冲突（409，如有）
- 未认证（401）和无权限（403，如有）

断言格式：检查 `code`、`message`、`data` 三个字段。

```bash
# 运行前确保容器已启动
make test-up
uv run pytest tests/<domain>/test_<domain>.py -v
```

测试必须通过再进入下一阶段。

---

## 阶段四：代码检查

按顺序运行，每步通过再执行下一步：

```bash
uv run ruff check --fix . && uv run ruff format .   # 自动修复格式问题
uv run ruff check .                                  # 确认 lint 干净
uv run ruff format --check .                         # 确认格式干净
uv run mypy app                                      # 类型检查，不能用 type: ignore 掩盖真实错误
```

或一次运行所有检查：

```bash
make ci
```

如果改动涉及认证、公开端点、JWT、CORS、rate limiting，运行 `/security-review`。

检查文档影响：如果 API、配置、测试命令、CI 有变化，更新对应文档（见 `.claude/rules/docs-maintenance.md`）。

---

## 阶段五：提交 commit

所有检查通过后执行 `/dev-workflow` 完成提交。

commit 格式：
```
<type>: <一句话说明做了什么，用祈使句>
```

类型参考：`feat` / `fix` / `refactor` / `test` / `docs` / `chore`

按意图分组，同一根因的变更放一个 commit，不相关的分开提交。
