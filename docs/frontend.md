---
doc_type: convention
status: active
authority: normative
scope: nextjs-frontend
last_reviewed: 2026-08-12
---

# 前端边界

`apps/web` 是 Next.js 16、React 19、Tailwind CSS 4 的 App Router 应用。

## 当前范围

- 只有根页面与 layout。
- 页面是静态 Launch Console，展示 workspace 与质量门禁。
- 没有 API 请求、认证流程、表单、客户端状态或动态路由。
- 没有组件测试或端到端测试；`test` 当前等价于 lint + typecheck。
- Web 可以在 API 未运行时独立启动。

不要把页面上的 `ready` 或 `active` 标签解释成运行时探测结果，它们是静态展示内容。

## 共享配置

`packages/config` 提供 TypeScript 配置和 ESLint ignores。只有实际被应用消费的配置才应进入共享 package；不要提前建立 UI kit、SDK 或状态层。

## 扩展顺序

出现真实业务页面时按需增加：

1. 环境变量与 typed API client；
2. API loading/error/empty states；
3. 认证与授权 UI；
4. 可复用组件；
5. 组件或浏览器测试。

任何 API 集成都必须保持明确的失败状态，并同步后端 CORS 与认证约束。
