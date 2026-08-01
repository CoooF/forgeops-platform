# EPIC-02.7 → EPIC-03 UI/契约交接

本文只定义可执行交接清单，不授权开始 EPIC-03。

## 前端模块边界

```text
app-shell/
studio/        canvas, node-library, inspector
debugger/      run controls, port emission, trace, evidence
builder/       main-agent goal, clarification, draft diff
results/       path, candidates, risk, evidence ledger, output
governance/    project, domain, permission, audit adapters
prototype/     isolated fixtures; production routes must not import
api-client/    generated or contract-checked versioned client
```

## 必须由 OpenAPI/JSON Schema 冻结

- WorkflowDefinition / WorkflowVersion / typed node 与 typed port；
- 执行 Agent 节点实例的模型、SkillBinding、McpBinding、Scope、预算、重试和失败出口；
- 主 Agent/Builder 会话与草稿 diff，且与执行图隔离；
- Run、NodeExecution、PortEmission、Trace、Evidence、Candidate、Review、ResultEnvelope；
- WorkflowVersion → DomainLock → ContextManifest → 数据快照 → Agent/模型/Skill/MCP 版本 → 人工操作的追溯链。

## 架构不变量

1. 主 Agent 不进入执行图，不具有 DATA/CONTROL 端口。
2. Skill/MCP 是执行 Agent 节点级绑定；不能只有主 Agent 能安装/调用。
3. 节点绑定必须版本化、可审计、可授权、可撤回；默认不跨节点继承。
4. 后端决定权限、发布和运行状态；前端不得推断成功。
5. UI Extension 只能使用受控、版本化、Schema 驱动 Host；不执行任意远程 JavaScript。
6. 未经产品负责人最终验收，状态不得变为 `ACCEPTED_FOR_EPIC_03_IMPLEMENTATION`。

## 进入 EPIC-03 的人工条件

- 产品负责人走查 `/design-preview/prototype` 并明确表示最终接受；
- EPIC-02.7 状态、截图、测试、提交和未实现边界准确；
- 另行生成并确认 EPIC-03 提示词。本任务本身不得进入实现。

