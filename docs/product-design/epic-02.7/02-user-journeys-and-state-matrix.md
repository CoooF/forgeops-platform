# EPIC-02.7 用户旅程与状态矩阵

状态：`PHASE_B_IN_PROGRESS`。以下均为方向 A 高保真本地原型，不代表后端能力。

## 四条连续旅程

1. **普通工程师**：项目 → 打开主 Agent → 查看目标理解与 Builder 草稿 diff → 工作流 → 选择执行 Agent → 查看该节点独立模型、Skill、MCP、Scope、预算与失败出口 → 原型校验 → 调试台错误/Evidence。
2. **领域管理员**：领域 → Registry → 组织 Installation → Overlay 产品入口 → Project DomainLock → 影响分析。Registry、Installation 与 DomainLock 跳回现有真实 API 页面；Overlay 仍是原型。
3. **项目负责人**：运行与推演 → 合成实际路径 → 三个候选比较 → Evidence Ledger → 风险/缺口 → 等待人工 → Advisory/Not Executed 结果。要求重算保持禁用，不创建真实 Run。
4. **调查人员**：结果 → WorkflowVersion → DomainLock → ContextManifest → 数据快照 → 三个执行 Agent 的模型/Skill/MCP 版本 → 人工操作。所有合成引用都有来源标签。

## 主 Agent 与执行 Agent

| 对象 | 产品位置 | 职责 | 明确禁止 |
| --- | --- | --- | --- |
| 主 Agent | 项目与工作室贯穿入口、右侧协作面板 | 目标理解、规划、协调、Builder 草稿、解释 | 无 DATA/CONTROL 端口；不进入工作流实际路径；不继承或调用执行节点 Skill/MCP；不持有生产写权限 |
| 执行 Agent 节点 | 工作流画布与 Agent/能力中心 | 读取 typed DATA、调用本节点装配能力、产生 typed DATA/CONTROL | 不继承主 Agent 配置；不同节点不得隐式共享模型、Skill、MCP、Scope 或预算 |

## 状态矩阵

| 类别 | 原型表达 | 安全处理 |
| --- | --- | --- |
| 首次/空/有数据 | 项目任务、节点库、候选列表、Evidence Ledger | 使用集中 fixture；不写数据库 |
| 加载/刷新/网络中断 | 真实 API 页面继续使用原有状态；原型无网络加载动画 | 原型不请求 `/v1` 或 `/health` |
| 无权限/跨组织/环境禁止 | 沿用真实 API 后端拒绝；原型入口显示来源 | 不用前端状态伪装授权成功 |
| 校验错误/版本过期/撤回 | 节点缺口、DomainLock/包状态入口 | 不修改既有后端校验 |
| 运行中/等待人工/部分结果/失败 | Run 页面只展示“本地合成”状态 | 不使用计时器或 Toast 冒充执行 |
| 数据质量/语义歧义/Evidence 不足 | 质量门、风险清单、Evidence 缺口 | 保留原因与恢复路径 |
| 模型不可用 | 执行 Agent 显示“待授权” | 不自动降级成已运行 |
| Advisory/Not Executed | 顶部边界、画布角标、Run 汇总持续可见 | 禁止显示“已执行/已发布” |
| 真实 API/混合/原型/未来能力 | 导航、页标题、模块项均显示 Source Badge | 真实后端仍是状态与权限真值 |

