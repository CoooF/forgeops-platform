# EPIC-02.7 产品负责人摘要

状态：`READY_FOR_PRODUCT_OWNER_REVIEW`。方向 A 高保真本地原型、文档、截图和工程门禁已完成，但产品负责人尚未最终验收；不得标记 `ACCEPTED_FOR_EPIC_03_IMPLEMENTATION`，不得进入 EPIC-03。

## 1. 一句话结论

ForgeOps 已形成以方向 A「静默控制台」为基线、画布优先、主 Agent 只协调、每个执行 Agent 独立装配 Skill/MCP 的完整高保真产品原型，同时保留现有真实 API 页面和全部安全边界。

## 2. 为什么新增 EPIC-02.7

02.5/02.6 的真实页面证明了项目、权限、Registry、DomainLock、语义、知识和 Context 闭环，却仍像后端对象验收台。02.7 先冻结产品 IA、核心工作台、运行调查、Agent 关系、设计系统和前端边界，避免 EPIC-03 在错误 UI/领域模型上实现真实执行。

## 3. 产品负责人选择了什么

2026-08-01 明确选择 A「静默控制台」作为完整原型基础：安静、精密、近白画布、适合长时间工作。明确纠正：Skill/MCP 属于每个执行型子 Agent 节点的独立装配，不是主 Agent 独占；主 Agent 不参与具体执行。

## 4. 开发前后对比

| 之前 | 现在 |
| --- | --- |
| 功能验收后台、对象卡片为主 | 项目入口 → 工作流画布 → Run/结果调查的连续产品任务 |
| 主 Agent 与执行 Agent 关系不清 | 主 Agent 无 typed ports；三个执行 Agent 各有独立模型、Skill、MCP、Scope、预算与失败出口 |
| Skill/MCP 像可直接加到画布的普通节点 | 能力库明确提示“选择执行 Agent 后装配”，每项显示节点私有 |
| 数据/Agent/运行等模块过于简单 | 统一 7 区 Shell，覆盖数据与知识、Agent 与能力、领域和治理 |
| 原型/真实/未来边界容易混淆 | 全局 BoundaryBar + 页级 Source Badge + 禁用动作持续区分 |

## 5. 四类用户如何使用

- 普通工程师：项目 → 主 Agent 拆目标 → Builder diff → 工作室 → 选择执行 Agent → 检查装配 → 校验/错误。
- 领域管理员：领域 → Registry → Installation → Overlay 入口 → DomainLock → 影响；真实能力回到现有 API 页面。
- 项目负责人：合成 Run → 实际路径 → 候选比较 → Evidence/风险/缺口 → 人工待办 → Advisory 输出。
- 调查人员：从结果追溯 WorkflowVersion、DomainLock、ContextManifest、数据快照、Agent/模型/Skill/MCP 版本和人工操作。

## 6. 主 Agent 与执行 Agent 节点如何区分

主 Agent 是深色项目协作面板，只负责目标理解、澄清、规划、Builder 草稿 diff 与解释；明确显示“没有 DATA/CONTROL 端口、不安装或调用执行节点 Skill/MCP、未调用模型”。执行 Agent 是画布 typed node，每个实例独立装配模型、Skills、MCP Servers、Scope、预算、重试和失败出口，默认不跨节点继承。

## 7. 哪些是真实 API，哪些是原型

`/` 继续提供 Project、成员/权限、Registry、Installation、DomainLock、Semantic/Knowledge、Context、Grounding、Impact 与 Audit 的真实 API 页面。`/design-preview/directions` 和 `/design-preview/prototype` 只使用隔离 TypeScript fixture/React 本地状态，不请求 `/v1`/`health`，不写数据库。Workflow/Run/Agent、数据库连接/Catalog/质量、候选/Review 均仍是原型或未来能力。

## 8. 三种视口与五分钟走查

- 1440×900：导航、节点库、画布、检查器、调试台完整并列；
- 1280×800：节点收紧但不重叠、不越界；
- 476×770：导航抽屉、纵向画布、检查器/调试台主滚动、全高主 Agent 面板，无横向溢出；
- 走查见 [EPIC-02.7-product-prototype.md](../runbooks/EPIC-02.7-product-prototype.md)。

## 9. 设计系统、组件和前端边界

建立暖白纸面、深绿主操作、橙色选中/风险、状态色、4/8px 节奏、44px 移动触控、可见焦点和 reduced-motion。新增隔离 `prototype/` 模块，集中 fixture、页面和 CSS；EPIC-03 交接拆分 Shell、Studio、Inspector、Debugger、Builder、Results、Governance 与契约生成 Client。

## 10. 测试、截图、依赖和提交证据

最终门禁：410 Python、41 contract、6 Vitest、8 Playwright E2E，覆盖率 87.18%；`make epic-02-7` 3/3，`make epic-02-6c` 290 通过，安全审计、构建和架构门通过。没有新增运行依赖，并移除原型的外部字体 CDN 依赖。验证源码提交：`91431fadce28e18bfbd4941403c936e64593d332`。截图及 SHA-256 见 [EPIC-02.7 Evidence](EPIC-02.7-evidence.md)。

## 11. 明确未实现

没有 WorkflowDefinition/Version 持久化、真实连线执行、Run/NodeExecution/PortEmission、断点/单步/Fork、Agent/LLM/RAG、Skill/MCP 安装或调用、Solver/Simulation/Candidate/Review、真实数据接入、外部写入、PLC/DCS 控制、企业身份、PREPROD/PROD 或业务 UAT。

## 12. 风险、限制和遗留问题

当前画布用于产品验证，不承诺大型图性能；路由是轻量 pathname/query 原型；真实页面尚未迁入统一 Shell；API Client 尚未从 OpenAPI 生成；候选/Evidence/Run 都是合成；画布库、许可证、React 19 兼容和可访问性仍需 EPIC-03 决策。

## 13. 产品负责人是否最终验收

尚未。产品负责人只完成方向 A 选择与 Agent 工具归属纠正，尚未明确接受最终完整原型。当前必须停在 `READY_FOR_PRODUCT_OWNER_REVIEW`。

## 14. 是否具备生成 EPIC-03 提示词的条件

工程材料已经具备，但人工条件尚未满足。只有产品负责人在真实页面走查后明确“接受 EPIC-02.7 最终原型”，才能记录 `ACCEPTED_FOR_EPIC_03_IMPLEMENTATION`，随后另行生成 EPIC-03 提示词；本任务不会自动进入。

