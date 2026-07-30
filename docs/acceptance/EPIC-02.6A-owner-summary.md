# EPIC-02.6A 产品负责人摘要

状态：`VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING`；`REQ-FDS-001` 仍是
`CLARIFYING / PARTIAL`。这不是产品验收、企业供应链验收或生产发布。

## 一句话结论

ForgeOps 开始拥有描述不同领域资源包的统一语法，并能为合法组合算出不会随输入顺序变化的
固定依赖清单。

## 为什么要做

FDS（ForgeOps Domain Specification，即“领域资源怎样描述、组合和约束”的产品语法）如果只
存在于文字约定中，不同团队会用不同方式描述 Domain（可复用领域定义）、Organization Overlay
（组织私有差异层）、Scenario（具体场景）和 Component（独立组件）；同一个项目还可能在不同
时间选到不同版本。这样会把循环依赖、版本冲突、私有内容泄漏和权限扩大带入后续 Registry
（领域包登记与管理服务）与运行时。本阶段先把“什么能组合、固定选择什么、为什么拒绝”变成机器规则。

## 前后对比

| 开发前 | 开发后 |
| --- | --- |
| 只有旧 Scenario Manifest（包说明书），不能独立表达领域、组织覆盖和组件 | 有 Domain、Organization Overlay、Scenario、Component 四类严格契约 |
| 依赖版本、来源、摘要和传递权限没有统一固定结果 | DependencyLock（依赖锁，即固定每个包版本、来源和摘要的清单）包含稳定拓扑、权限/预算差量和 SHA-256 内容指纹 |
| 相同候选的输入顺序可能影响选择 | 候选会规范排序和回溯，乱序输入与重复运行得到相同锁摘要 |
| 非法层级、循环、冲突和私有依赖缺少统一机器结果 | 非法组合返回稳定错误码、路径和顺序，而且不返回部分锁 |
| 旧 Scenario 与 FDS 的关系不清楚 | 两个旧合成包无修改地生成“可兼容但事实有限”的报告，不补造缺失能力 |

## 用户可见变化：现在能做什么、在哪里看

这是 FDS 契约内核，没有新增领域包管理页面。产品/工程人员现在可以：

- 用 `make fds-owner-demo` 查看一个合法五节点合成组合的固定依赖锁和一个真实拒绝结果；
- 在 `contracts/fds/` 查看四类 Manifest（包说明书）Schema、DependencyLock、兼容报告、
  多层合成图和第二领域形状；
- 用 `make epic-02-6a` 验证合法/非法组合、乱序输入、循环、冲突、公私边界、权限扩大和篡改；
- 在 [EPIC-02.6A Evidence](EPIC-02.6A-evidence.md) 和
  [机器证据](generated-epic-02.6a-evidence.json) 查看固定结果、源码绑定和限制。

本阶段只验证 Organization Overlay 的契约和依赖边界，没有把它安装到真实组织或 Project。

## 不可见地基

- 四类严格、版本化、未知字段默认拒绝的 FDS Manifest，以及十一类 Component；
- 固定候选排序、最高兼容版本、确定性回溯、依赖优先拓扑、错误排序和摘要算法；
- 公共 Domain 不能直接或间接依赖私有 Overlay，层级方向和命名空间冲突默认拒绝；
- 传递权限与资源预算只计算差量，不产生授权，锁明确记录 `authorizationEffect=NONE`；
- 失败不产生部分锁或运行状态，锁明确记录 `runtimeStateCreated=false`；
- 旧 Scenario 先走原校验器，保留标识、摘要、权限和历史语义，不虚构 FDS 事实；
- Schema、锁、兼容报告连续导出，以及源码/wheel 依赖方向扫描。

## 五分钟验证路径

在仓库根目录运行：

```bash
make fds-owner-demo
```

无需阅读源代码，输出中应同时看到：

1. `legalPackage.status` 为 `LOCKED`，节点数为 5，锁摘要固定为
   `sha256:39dd6be726ec8d0fd303e9ff324df2eebc9b5ecfe7531cdc490b5d40b164530b`；
2. `legalPackage.authorizationEffect` 为 `NONE`，`runtimeStateCreated` 为 `false`；
3. `illegalPackage.status` 为 `REJECTED`，错误码为 `DEPENDENCY_MISSING`；
4. `illegalPackage.partialLockReturned` 为 `false`。

如需同时复核输入顺序不影响结果，可追加运行以下两个窄范围用例，无需重新跑全量门：

```bash
uv run pytest -q tests/unit/test_fds_resolver.py \
  -k 'multilayer_graph_produces_fixed_topological_lock_without_runtime_state or candidate_order_and_repeated_runs_do_not_change_lock'
```

期望两个用例通过，证明合法多层包产生固定 DependencyLock，候选输入反转和重复运行也不改变
锁摘要。这是纯本地契约运算，不访问 API、数据库、网络或真实数据。

## 成功案例

合法合成图按 Component → Domain → Domain → 私有 Organization Overlay → Scenario 组成五层依赖。
解析器固定精确版本、来源、内容摘要、依赖边和权限/预算差量；无论候选清单如何乱序，最终
DependencyLock 摘要都保持一致。

## 拒绝或失败案例

- 缺少必需组件稳定返回 `DEPENDENCY_MISSING`，且没有部分锁；
- 版本范围不兼容、循环依赖和直接冲突都会以稳定代码、路径和顺序返回；
- 公共 Domain 直接或间接依赖私有 Overlay 会被拒绝，避免私有内容污染公共发布；
- 传递依赖请求了根包未接受的权限或超出预算时会失败，不会顺便扩大授权；
- 相同包 ID/版本摘要冲突、锁摘要被篡改或可执行组件未声明隔离 Worker 边界也会被拒绝。

这些拒绝由 `TEST-FDS-DEPENDENCY-001`、`TEST-FDS-LAYER-001`、
`TEST-FDS-PERMISSION-001` 和 `TEST-FDS-SEC-001` 的固定负面矩阵验证。

## 明确未实现和不得对外宣称

- 没有数据库 Registry、领域包目录、Artifact 下载、安装 API 或前端管理页面；
- 没有 Domain/Overlay 安装、授权、发布、撤回传播或 Project DomainLock；
- 没有本体/术语注册、语义映射/查询、约束、Grounding（把术语绑定到可靠来源）或影响分析；
- 没有知识上传、存储、索引、RAG（检索后辅助生成）或 Context Compiler（把获准上下文组装给运行时）；
- 没有 Agent/工作流运行时、模型调用、外部网络、真实数据或任何业务行为；
- 没有钢帘线排产、设备诊断、跨行业真实 E2E（端到端验证）或生产标准声明。

EPIC-02.6B Registry/Project DomainLock 和 EPIC-02.6C 语义/知识运行时均为 `NOT_STARTED`。

## 风险与限制

- 所有新 fixture 都是 `FIRST_PARTY_LOCAL`、`SYNTHETIC`，即第一方本地合成数据；
- 本地 SHA-256 attestation（摘要一致性声明）不等于企业签名、发布者认证或许可证法律审查；
- `reference-domain-a` 只证明同一契约能描述第二种领域形状，不是非制造真实 E2E，G5B 仍阻塞；
- Legacy Adapter（旧包适配层）只证明旧包可生成兼容输入，不证明运行迁移、DomainLock 或
  replay（按历史重放）；
- PostgreSQL、企业 OIDC/Secret/网络、PREPROD/PROD、真实数据和业务 UAT 均未验证；
- 企业 G0/G1/G2、业务 G4/G5A/G5B 和生产发布门没有因本地契约测试而提升。

## 完成证据：需求、测试、Evidence 和提交

| 项目 | 对应内容 |
| --- | --- |
| 需求 | [EPIC-02.6A 需求](../requirements/EPIC-02.6A-fds-contract-kernel.md)；`REQ-FDS-001` 仅 `CLARIFYING / PARTIAL`，`REQ-SDK-001` 兼容输入 |
| 决策 | [ADR-0006](../adrs/0006-fds-contract-kernel-and-lock.md) |
| 关键测试 | `TEST-FDS-CONTRACT-001`、`TEST-FDS-DEPENDENCY-001`、`TEST-FDS-LAYER-001`、`TEST-FDS-PERMISSION-001`、`TEST-FDS-LOCK-001`、`TEST-FDS-LEGACY-001`、`TEST-FDS-XDOM-CONTRACT-001`、`TEST-FDS-SEC-001`、`TEST-ARCH-003` |
| 人读证据 | [EPIC-02.6A Evidence](EPIC-02.6A-evidence.md) |
| 机器证据 | [generated-epic-02.6a-evidence.json](generated-epic-02.6a-evidence.json)，SHA-256 `3381778550a68809608b1da7c7aa769102c226b62991bab548c6da92695dd5dc` |
| 实现提交 | `db39d0eb627cd0b5d1af653bb17bc042bfa66757` |
| 最终验证源码 | `f06f60145a402b6669baf12ad0b561a77c00a82f` |
| 最终证据提交 | `1f68ae5adfb9e00e69572c32379c688241b577c8` |

最终证据记录 40 个 FDS 聚焦测试、254 个全量 Python 测试、41 个独立契约测试、4 个 Web
测试和 1 个浏览器 E2E，综合行/分支覆盖率 89.78%，17 个 FDS JSON 连续导出摘要一致；这些
是本地契约工程证据，不是 FDS 产品运行验收。

## 下一步选择与产品负责人决策

本阶段只解锁了“可以设计下一步”，没有自动批准 02.6B 或 02.6C。产品负责人现在需要决定：
是否接受 02.6A 仅为契约内核的边界；是否为未来 02.6B 指定 Platform、Security、Artifact 和
Project Owner；以及是否先补企业签名/许可/私有制品前置。02.6B 必须另开任务和审批，02.6C
还必须等待语义/知识 Owner、最小 competency questions（必须能回答的领域问题）和授权查询边界。
本任务到此停止，不进入 02.6B/02.6C。
