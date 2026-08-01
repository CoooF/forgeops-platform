# EPIC-02.7 原型与真实状态边界

## 路由隔离

- `/`：既有 Project、Registry、DomainLock、Semantic/Knowledge、Context、成员和审计真实 API 页面。
- `/design-preview/directions`：阶段 A 方向档案；不调用 API。
- `/design-preview/prototype`：阶段 B 方向 A 高保真原型；只读取 `prototype/prototype-fixture.ts` 并使用 React 本地状态。

原型不得请求 `/v1`、`/health`，不得写数据库、安装 Skill、连接 MCP、创建 Workflow/Run、调用模型或触发工业系统动作。按钮可改变浏览器内视图，但不会显示后端成功 Toast。

## 来源标签

| 标签 | 含义 |
| --- | --- |
| 真实 API | 入口映射到已有受权限保护的 API/数据库闭环 |
| 混合边界 | 页面同时包含真实入口和明确原型/未来能力 |
| 本地原型 | 静态 TypeScript fixture + 浏览器内存 |
| 未来能力 | 只说明产品位置；控件禁用或解释不可用原因 |

## Agent 安全边界

- 主 Agent 是项目协作层，无 typed ports，不参与工作流执行，不继承子 Agent 工具。
- 每个执行 Agent 节点有独立 `model/skills/mcps/permissions/budget` 装配；原型只展示绑定草稿。
- “安装 Skill”“连接 MCP”“运行”“发布”“要求重算”不会产生外部副作用；未接后端的动作保持本地说明或禁用。
- Evidence、Trace、候选和 Run ID 均标记为合成，不作为真实运行证据。

