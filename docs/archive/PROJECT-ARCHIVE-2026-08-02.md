# ForgeOps 项目封存记录

> 封存日期：2026-08-02（Asia/Shanghai）  
> 项目状态：`PAUSED_ARCHIVED_BY_PRODUCT_OWNER`  
> Git 标签：`forgeops-archive-2026-08-02-epic-02.7-partial`  
> 封存前功能提交：`540afb005aabf4bd0b9c527a95f4ec351eb830f9`  
> 数据边界：仅本地合成数据，没有企业、PREPROD 或 PROD 验收

## 1. 封存决定

产品负责人决定暂停并封存 ForgeOps。原因是当前产品范围、工业业务验证、生产工程、安全治理和持续开发投入超过个人现阶段可稳定承担的能力与精力，不是因为已经证明产品方向无价值，也不是因为系统已经完成。

封存后不继续生成或执行 EPIC-03 及后续任务，不提高任何需求、企业发布门或业务有效性状态。恢复必须由产品负责人明确决定，并从本记录的恢复门开始。

## 2. 当前最准确的完成状态

| 范围 | 封存状态 | 准确含义 |
| --- | --- | --- |
| EPIC-01 | `VERIFIED`，仅本地合成工程 | 构建、迁移、测试、审计、制品和安全门的工程基线 |
| EPIC-02 | `VERIFIED`，仅本地合成工程 | 通用包、生命周期、Port 和安全边界契约 |
| EPIC-02.5 | `VERIFIED_FOR_LOCAL_SYNTHETIC_ENGINEERING` | 组织、工作空间、项目、身份、Scope、权限和真实 Project Center |
| EPIC-02.6A | `VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING` | FDS Manifest、分层组合和确定性 DependencyLock |
| EPIC-02.6B | `VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING` | Registry、组织安装、Project DomainLock 和撤回影响 |
| EPIC-02.6C | `VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING` | 语义/知识版本、确定性 Context、结构化 Grounding 和影响分析薄切片 |
| EPIC-02.7 | `READY_FOR_PRODUCT_OWNER_REVIEW` | 方向 A 高保真交互原型、设计系统、截图和测试已形成，但产品负责人未最终验收 |
| EPIC-03 及以后 | `NOT_STARTED / NOT_AUTHORIZED` | 没有真实 Workflow/Run/Agent/调试器、Solver、Simulation、Candidate 或 Review 运行时 |

`EPIC-02.7` 不能写成完成。产品负责人只确认过方向 A 和 Agent/Skill/MCP 的归属纠正，没有明确接受最终完整原型，因此没有 `ACCEPTED_FOR_EPIC_03_IMPLEMENTATION`。

## 3. 已经存在的可用资产

- 独立生产仓库、锁定依赖、测试、CI 定义、迁移和本地运行手册；
- 通用平台契约、FDS v0.1、领域/组织扩展/场景/组件分层；
- 组织、工作空间、项目、成员和默认拒绝的权限模型；
- Registry、Installation、Project DomainLock、语义/知识/Context/Grounding 的真实本地 API 与页面；
- 产品范围、架构、威胁模型、风险、追踪矩阵、发布门、Owner Summary 和机器证据；
- 方向 A「静默控制台」高保真产品原型，包含画布、主 Agent、执行 Agent 装配、运行调查、结果和外围模块；
- EPIC-03 工作流运行时、typed ports、结果信封和调试器的设计输入，但没有实现。

## 4. 明确没有完成

- 企业身份、PostgreSQL 服务级验证、备份恢复、PREPROD/PROD 和 UAT；
- 真实钢帘线领域本体、企业映射、知识许可审核和真实数据；
- WorkflowDefinition/Version 持久化和真实画布执行；
- Run、NodeExecution、PortEmission、断点、单步、Fork Run 和 Result Collector；
- Agent/LLM/RAG、模型路由、Skill/MCP 安装与调用；
- Solver、Simulation、Candidate、Evaluation、Review 和排产业务闭环；
- 任何外部正式系统写入、RPA、PLC/DCS/设备控制；
- 企业安全、业务价值、跨行业泛化或生产级产品声明。

## 5. 封存时的安全边界

- `real_data_enabled=false`；
- `local_synthetic_only=true`；
- 不调用外部模型；
- 不连接企业身份或真实业务系统；
- PREPROD/PROD 不允许 Mock 动作适配器；
- 没有生产写适配器、正式写凭据或设备控制路径；
- 原型页面不创建真实 Workflow、Run 或 Agent 执行记录。

## 6. 关键入口

- 总进度：[PRODUCT-OWNER-PROGRESS.md](../acceptance/PRODUCT-OWNER-PROGRESS.md)
- 02.7 状态：[EPIC-02.7-owner-summary.md](../acceptance/EPIC-02.7-owner-summary.md)
- 02.7 证据：[EPIC-02.7-evidence.md](../acceptance/EPIC-02.7-evidence.md)
- 原型走查：[EPIC-02.7-product-prototype.md](../runbooks/EPIC-02.7-product-prototype.md)
- EPIC-03 交接输入：[06-epic-03-ui-contract-handoff.md](../product-design/epic-02.7/06-epic-03-ui-contract-handoff.md)
- 项目 README：[README.md](../../README.md)

## 7. 恢复方式

从 Git 标签恢复只读检查：

```bash
git switch --detach forgeops-archive-2026-08-02-epic-02.7-partial
```

从标签创建恢复分支：

```bash
git switch -c resume/forgeops forgeops-archive-2026-08-02-epic-02.7-partial
uv sync --frozen --all-groups
pnpm install --frozen-lockfile
make verify
make epic-02-7
```

若使用 `.bundle` 恢复到新目录：

```bash
git clone forgeops-platform-full-history-2026-08-02.bundle forgeops-platform
cd forgeops-platform
git switch -c resume/forgeops forgeops-archive-2026-08-02-epic-02.7-partial
```

恢复后的第一个产品动作不是直接实现 EPIC-03，而是：

1. 重新打开并走查 `/design-preview/prototype`；
2. 产品负责人决定接受、要求修改或废弃 EPIC-02.7 原型；
3. 只有明确接受后，记录 `ACCEPTED_FOR_EPIC_03_IMPLEMENTATION`；
4. 重新复核预算、开发责任、Git 远端、企业数据授权和安全 Owner；
5. 另行生成 EPIC-03 提示词。

## 8. 封存验证

封存标签必须是 annotated tag，并指向包含本记录的干净提交。仓库外备份应至少包含：

- 完整 Git 历史 `.bundle`；
- 标签源码快照；
- 根规划、旧 Demo、视频分析与原始材料包；
- SHA-256 校验文件和恢复说明。

封存不删除本地工作目录、虚拟环境、数据库或生成物；这些不是 Git 标签的一部分，是否长期保留由产品负责人另行决定。

