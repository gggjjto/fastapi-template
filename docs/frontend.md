---
doc_type: convention
status: active
authority: normative
scope: nextjs-frontend
last_reviewed: 2026-08-17
---

# 前端边界

前端由两个独立的 Next.js 16、React 19、Tailwind CSS 4 App Router 应用组成：

- `apps/admin`：管理后台与浏览器 BFF。
- `apps/web`：面向业务的空白应用骨架。

## 当前范围

- `apps/admin` 提供登录、当前用户、健康状态、租户/成员/邀请，以及 Crawler 目标和任务管理页面。
- Admin Route Handlers 代理后端 API，并使用 HttpOnly Cookie 保存 access/refresh token；修改请求执行同源检查。
- `apps/web` 当前只有欢迎页与 layout，等待真实业务功能。
- 不引入全局状态库或 UI kit，页面使用原生 `fetch`、React state 和现有 CSS。
- 尚无浏览器端到端测试；Admin 使用 Node 内置测试覆盖 BFF 安全边界，业务 Web 的 `test` 等价于 lint + typecheck。
- 两个应用都可以在 API 未运行时独立启动。

开发端口：业务 Web 使用 `3000`，Admin 使用 `3001`。

## 共享配置

`packages/config` 提供 TypeScript 配置和 ESLint ignores。只有实际被应用消费的配置才应进入共享 package；不要提前建立 UI kit、SDK 或状态层。

## 扩展顺序

业务 Web 出现真实页面时按需增加：

1. 环境变量与 typed API client；
2. API loading/error/empty states；
3. 认证与授权 UI；
4. 可复用组件；
5. 组件或浏览器测试。

任何 API 集成都必须保持明确的失败状态，并同步后端 CORS 与认证约束。
