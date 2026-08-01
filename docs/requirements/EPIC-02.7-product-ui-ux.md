# EPIC-02.7 产品 UI/UX 与高保真原型要求

状态：`IN_PROGRESS / DIRECTION_A_SELECTED`

## 目标

在不实现 WorkflowDefinition、Run、PortEmission 或 Agent Runtime 的前提下，先冻结 ForgeOps 的产品信息架构、工作流工作室视觉方向、真实 API 与原型边界，以及 EPIC-03 可直接承接的前端模块边界。

## 阶段 A 当前范围

- 审计 EPIC-02.5/02.6 的真实 Project、Registry、DomainLock、Semantic/Knowledge、Context 与权限页面；
- 在独立路径 `/design-preview/directions` 提供 A/B/C 三套同一工作台场景的可比较方向；
- 每套包含 8 模块产品级导航、全局上下文、能力库、白色全幅画布、8 个 typed DATA/CONTROL 节点、检查器、调试底栏和主 Agent 入口；
- 产品壳层覆盖项目、工作流、运行与推演、数据与数据库、主 Agent 中心、Agent 与能力、领域和治理，并逐项显示真实 API / 混合边界 / 产品原型；
- 页面持续显示“视觉方向预览 / 本地合成 / 未接 Workflow、Run、Agent 后端 / 未运行 / 建议未执行”；
- 原型使用隔离 TypeScript fixture 和浏览器内存，不调用 API、不写数据库、不伪造成功状态；
- 真实 API 页面继续由 `/` 提供，权限拒绝与安全状态不改变。

## 人工门

1. 产品负责人已于 2026-08-01 明确选择 A「静默控制台」，阶段 B 可以实施；
2. 执行型子 Agent 节点各自独立装配模型、Skill、MCP、权限、预算和失败出口；主 Agent 只做项目级目标理解、规划、协调、Builder 草稿与解释，不参与具体执行；
3. 最终原型完成后仍须再次等待产品负责人明确验收；
4. 在最终明确验收前，不得写入 `ACCEPTED_FOR_EPIC_03_IMPLEMENTATION`，不得进入 EPIC-03。

## 明确未实现

Workflow/Version 持久化、节点连线执行、Run、NodeExecution、PortEmission、断点、单步、Fork Run、Agent/LLM/RAG、Skill/MCP 实际调用、Solver、Simulation、Candidate、Review、真实数据接入、外部系统写入与工业控制均未实现。
