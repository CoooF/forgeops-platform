# ForgeOps Platform

> **本体驱动的领域智能体构建、编排、推演、评测与持续进化平台。**

ForgeOps 是一个仍在探索中的平台构想：把领域本体、企业知识、数据、Agent、模型、Skill、MCP、算法和仿真能力装配到同一套可追溯的工作流中，让普通工程师与领域专家也能构建、推演和评估自己的智能体系统。

它不把大模型当作可以绕过业务规则的万能主脑，也不认为可控工作流和自主 Agent 必须二选一。ForgeOps 尝试建立一种中间形态：**确定的部分由契约、节点、权限和运行时控制；不确定的部分交给有边界的 Agent；最后结果保留证据、版本和人工决定。**

![ForgeOps 方向 A 高保真工作流原型](docs/product-design/epic-02.7/screenshots/prototype-a-studio-1440x900.png)

> 上图是 EPIC-02.7 的高保真产品原型，不是真实 Workflow/Run/Agent Runtime。当前仓库不会伪装尚未实现的能力。

> **当前状态：** 项目于 2026-08-02 由产品负责人暂停并封存，状态为 `PAUSED_ARCHIVED_BY_PRODUCT_OWNER`。标签为 `forgeops-archive-2026-08-02-epic-02.7-partial`；EPIC-02.7 已形成原型但未最终验收，EPIC-03 未开始。暂停的原因是生产级建设所需的跨专业能力与长期投入超出个人现阶段可稳定承担的范围，而不是已经证明这条理论没有价值。详见[项目封存记录](docs/archive/PROJECT-ARCHIVE-2026-08-02.md)。

## 为什么会有 ForgeOps

这个想法最初来自钢帘线行业的排产问题：企业已经有 APS、MES、ERP 和大量工艺知识，但“接入一个大模型”并不会自动理解设备能力、工艺约束、规则来源、数据质量和责任边界。

继续推演后，问题逐渐从“做一个排产 Agent”变成了：

- 一个领域的术语、关系、规则、知识和数据映射，能否在多个场景中复用；
- Agent 能否像节点一样被组合，但仍保留自己的模型、Skill、MCP、权限、预算和失败出口；
- 数据能否先被治理、版本化和持久化，再以可追溯快照进入 Agent，而不是直接塞进 Prompt；
- Solver、固定算法、仿真、人工审批和 Agent，能否在同一个流程中各自做擅长的事情；
- 普通工程师能否在 Builder Agent 的协助下拆解业务、搭建流程，而不需要先成为 AI 平台开发者；
- 同一套平台能否装配不同领域，而不是永远与制造业或钢帘线绑定。

钢帘线排产因此只是第一参考场景，不是 ForgeOps 的产品边界。

## 核心构想

### 1. 本体不是一份知识图谱，而是 Agent 的领域上下文底座

领域本体负责定义稳定概念、关系、约束、术语和证据引用；Organization Overlay 负责企业自己的编码、映射、规则和私有知识。Agent 的回答、工具选择和流程输出应尽量绑定这些可版本化资产，而不是只依赖一段临时 Prompt。

### 2. 用领域包完成跨行业装配

```text
ForgeOps Platform Core
  -> FDS / Domain & Scenario SDK
    -> Domain Package
      -> Organization Overlay
        -> Scenario Package
```

- Platform Core 只提供 Project、Workflow、Run、Agent、Evidence、Simulation、Review 等通用能力；
- Domain Package 提供可复用领域语义、知识、Agent、Skill 和数据映射模板；
- Organization Overlay 保存企业私有术语、编码、规则和系统绑定；
- Scenario Package 组合具体流程、算法、仿真、评测、合成数据和 UI Extension。

这套内部协议暂称 **FDS（ForgeOps Domain Specification）**。它是本项目提出的草案，不是公共标准，也没有行业背书。

### 3. 工作流与 Agent 自主性不是对立关系

画布负责可观察、可中断、可测试、可重放的执行结构；Agent 节点负责限定范围内的分析、协作和工具调用。主 Agent 帮助理解目标、拆解流程和解释结果，但不能自动安装能力、自授权、发布流程或修改历史运行。

### 4. 模型只是可替换的“脑”，能力属于节点

每个执行 Agent 可以独立绑定不同模型，并独立装配 Skill、MCP、数据 Scope、预算、重试和失败出口。模型可以更换，业务契约、证据和安全边界不应随模型一起消失。

### 5. 数据先治理，再进入智能体

业务系统数据应先进入 DataProduct、质量规则、版本快照和 Evidence 管理，再由工作流按授权引用。数据接口、数据库、知识库和 MCP 可以成为节点能力，但不能绕过组织、项目、用途和时间范围。

### 6. 推演输出是建议，不是自动执行

排产、故障判断、工艺优化或其他领域场景可以产生多个 Candidate，通过 Solver、Simulation 和 Evaluation 比较，再交给人工 Review。ForgeOps 永久保留 Advisory / Not Executed 边界，不直接控制 PLC/DCS，也不自动修改正式业务数据。

### 7. 能力市场是可能的未来，而不是当前完成项

领域包、Agent、Skill、MCP、算法、连接器和工作流模板未来可以进入企业能力目录，进一步演化为受治理的能力市场。但制品、许可、安装、授权、绑定、使用和交易必须分离，不能把“能找到”误认为“可以运行”。

## 它不是什么

- 不是已经完成的工业 Agent 平台；
- 不是 APS、MES 或 ERP 的替代品；
- 不是聊天框套业务页面；
- 不是只会画连线但无法真实运行的流程图工具；
- 不是让通用 Agent 直接控制 PLC、DCS 或安全联锁；
- 不是已经验证的“本体大模型”产品或行业标准；
- 不是已经证明跨行业通用性的成熟架构。

## 现在做到了哪里

| 范围 | 当前证据 | 仍未完成 |
| --- | --- | --- |
| 工程基线 | 锁定依赖、迁移、测试、构建、SBOM、安全和架构门 | 企业部署、备份恢复和运维体系 |
| 项目与权限 | Organization、Workspace、Project、Membership、Scope 和默认拒绝授权 | 企业 OIDC/SCIM 与正式权限治理 |
| FDS | Domain/Overlay/Scenario/Component Manifest、确定性 DependencyLock、Registry、Installation、Project DomainLock | 企业制品、签名、许可与跨行业验证 |
| 语义与知识 | 版本化 Ontology/Terminology/Mapping/Knowledge、ContextManifest、结构化 Grounding 和影响分析薄切片 | 真实行业本体、RAG、图数据库和业务正确性 |
| 产品体验 | 方向 A 工作流、主 Agent、执行 Agent、运行调查和结果页高保真原型 | 产品负责人最终验收与真实后端接入 |
| Workflow/Agent | 只有设计契约和 UI 原型 | WorkflowVersion、Run、PortEmission、调试器、Agent/LLM/Skill/MCP 实际运行 |
| 参考场景 | 只有合成契约 fixture | 钢帘线排产、设备诊断、真实数据、Solver、Simulation 和业务 UAT |

所有 `VERIFIED` 都只表示限定范围内的本地合成工程证据，不代表企业、业务或生产验收。

## 为什么公开

这个仓库公开，不是为了宣称“产品已经做完”，而是希望让这套尚未完成的理论被看见、被质疑，也可能被继续推进。

尤其希望遇到这些方向的同行：

- 认可“本体/领域包 + Agent + 工作流 + 仿真评测”组合路线的人；
- 本体工程、知识图谱、语义建模和领域驱动设计实践者；
- Agent Runtime、MCP、Skill、模型路由和多 Agent 协同开发者；
- 可视化工作流、调试器、分布式执行和可观测性工程师；
- 优化算法、运筹、离散事件仿真和决策科学从业者；
- 工业、医疗、能源、供应链、电商或其他领域的业务专家；
- 关心 AI 权限、安全、Evidence、审计和人机责任边界的人；
- 愿意把一个大构想收缩成可验证、小步推进产品的人。

你不需要完全认同现有设计。对 FDS、本体边界、Agent 自主性、工作流抽象、商业模式或实现顺序的反对意见同样有价值。

## 交流与参与

- 在 [GitHub Discussions](https://github.com/CoooF/forgeops-platform/discussions) 讨论理论、架构、场景和合作方式；
- 在 [Issues](https://github.com/CoooF/forgeops-platform/issues) 提出具体问题、反例或可验证场景；
- 阅读 [Contributing](CONTRIBUTING.md) 了解当前工程证据要求；
- 从 [产品负责人进度总览](docs/acceptance/PRODUCT-OWNER-PROGRESS.md) 了解哪些是真的、哪些仍是设想；
- 从 [EPIC-02.7 产品原型说明](docs/acceptance/EPIC-02.7-owner-summary.md) 和 [EPIC-03 UI 交接](docs/product-design/epic-02.7/06-epic-03-ui-contract-handoff.md) 理解暂停点。

当前仓库采用 proprietary evaluation 声明，**公开可见不等于已经采用开源许可证**。欢迎先交流；准备复用代码或提交较大实现前，请通过 Discussion/Issue 确认许可与治理方式。许可证本身也是项目恢复时需要共同决定的问题。

## 产品负责人进度与五分钟验证

从 [产品负责人进度总览](docs/acceptance/PRODUCT-OWNER-PROGRESS.md) 进入各 Epic 的大白话说明、
成功/拒绝案例、五分钟验证路径、明确未实现项和证据提交。当前结果均不代表企业验收或生产发布。

## 已实现的工程基线

- 领域无关的平台契约和版本化执行信封；
- Scenario Manifest/pack、兼容校验、本地摘要证明、权限、预算、迁移和生命周期语义；
- 安装、Grant、Binding、环境发布和启用相互分离的包生命周期；
- 持久化 Principal、Organization、Workspace、Project、Membership 和真实项目包绑定；
- 可替换 `AuthPort`、集中式 `AuthorizationPort`、本地合成身份和追加式决策证据；
- FastAPI 健康、包 Registry、资格、审计、状态和指标接口；
- SQLAlchemy 持久化、PostgreSQL Compose 配置和本地 SQLite 开发配置；
- 结构化日志、Trace、Prometheus 指标和内容寻址本地对象存储；
- 使用真实 API 的 React Project Center、Registry、DomainLock、Semantic/Knowledge 和 Context 页面；
- Python/TypeScript 锁文件、迁移、CI、SBOM、安全、测试和架构检查；
- FDS Domain/Organization Overlay/Scenario/Component 契约与确定性依赖锁；
- FDS Registry、组织 Installation、不可变 Project DomainLock 和撤回影响；
- 绑定锁定组件版本的 Ontology/Terminology/Mapping/KnowledgeAsset、确定性 ContextManifest、结构化 Grounding 和影响分析。

## 明确非范围

当前没有 OR-Tools 排产、异常诊断、真实或脱敏企业数据、企业 IdP/Secret/网络、外部模型调用、运行时第三方 Python/JavaScript 加载、外部系统写入或工业控制能力。`industrial-agent-demo` 不属于本生产仓库。

## 本地运行（不使用 Docker）

```bash
uv sync --frozen --all-groups
uv run alembic upgrade head
uv run uvicorn forgeops.api:create_app --factory --host 127.0.0.1 --port 8000
```

本地配置把元数据写入 `.local/forgeops.db`，对象写入 `.local/objects`。它只用于开发回退；PostgreSQL 仍是目标适配器。

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
curl -H 'X-ForgeOps-Actor: local-owner' http://127.0.0.1:8000/v1/platform/status
curl -H 'X-ForgeOps-Actor: local-owner' http://127.0.0.1:8000/v1/me
curl -H 'X-ForgeOps-Actor: local-owner' http://127.0.0.1:8000/v1/organizations
```

`X-ForgeOps-Actor` 只是 DEV/TEST 身份查找，不直接授予权限。`local-owner`、`local-editor`、`local-viewer`、`local-outsider` 和 `local-disabled` 的访问权由持久化 Membership 决定；企业身份尚未连接。

## 本地服务拓扑

可使用 Docker 时：

```bash
docker compose -f deploy/local/compose.yaml config --quiet
docker compose -f deploy/local/compose.yaml up --build
```

该拓扑只用于本地合成开发，不能直接复用于 PREPROD 或 PROD。

## 可重复验证

```bash
make bootstrap
make verify
make migration-proof
make smoke
make web-smoke
make e2e
make epic-02-5
make epic-02-6a
make epic-02-6b
make epic-02-6c
make epic-02-6c-owner-demo
make sbom
make evidence
```

准确的本地边界见 [EPIC-02.6C Evidence](docs/acceptance/EPIC-02.6C-evidence.md) 和
[02.6C requirement](docs/requirements/EPIC-02.6C-semantic-knowledge-runtime.md)。
[Local development](docs/runbooks/local-development.md) 包含五分钟产品负责人和浏览器走查路径。
