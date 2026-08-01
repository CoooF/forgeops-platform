# EPIC-02.7 现有页面迁移图

本任务不重写真实 API 页面，只冻结未来统一 Shell 的映射。

| 现有页面/能力 | 目标产品区域 | EPIC-02.7 处理 | 后端边界 |
| --- | --- | --- | --- |
| Project Center / Overview | 项目 | 保留真实入口；未来套统一 Shell | API、Scope、归档规则不变 |
| Members | 项目 / 治理 | 合并任务入口，不复制权限判断 | 后端授权真值 |
| Scenario Installation / Binding | Agent 与能力 / 已安装 | 转二级任务；不把绑定等同授权/发布 | 保留现有契约 |
| Domain Registry / Installation | 领域 | 连续为 Registry → Installation | 真实 API |
| Project DomainLock / Impact | 领域 | 连续为 Lock → 影响调查 | 真实 API 与撤回拒绝不变 |
| Semantic & Knowledge | 数据与知识 / 语义 | 保留真实入口 | 真实 API |
| Project Context / Grounding | 数据与知识 / Evidence | 保留真实入口 | 真实 API、预算与歧义语义不变 |
| Audit | 治理 | 统一入口 | 追加式真实证据 |
| Workflow Studio / Run / Agent | 新产品核心 | 仅高保真本地原型 | 尚无后端 |
| 数据库连接/Catalog/Schema/质量 | 数据与知识 | 只冻结 IA | 不收凭据、不连接数据库 |

EPIC-03 前必须把 Shell、Studio、Inspector、Debugger、Builder、Results、Governance 分模块，并生成/校验版本化 TypeScript API Client；可以后置大型画布性能、多用户协作和插件市场。

