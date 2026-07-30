# EPIC-02.6A 产品负责人摘要

一句话结论：ForgeOps 现在能在本地、无网络、无数据库的条件下判断一个 FDS
组合是否合法，并为合法组合生成可重复的固定依赖锁；它还不是 FDS 运行平台。

## 为什么要做

如果没有这一层机器契约，Domain、组织私有覆盖、Scenario 和组件只能靠文档约定，
同一项目可能在不同时间选到不同依赖，也无法在安装前稳定拦截循环、私有内容污染和
权限扩大。后续 Registry、Project DomainLock 和语义运行时都会建立在不可靠的输入上。
本阶段先把“什么可以组合、最后锁定什么、为什么拒绝”变成可重复验证的产品规则。

## 前后对比

| 之前 | 现在 |
| --- | --- |
| 只有单个 Scenario Manifest，无法独立表达 Domain、组织覆盖层和组件 | 有严格的 Domain、Organization Overlay、Scenario、Component 四类契约 |
| 依赖版本、来源、摘要和传递权限没有统一固定锁 | 相同输入总是得到相同版本、拓扑顺序、权限/预算差量和 SHA-256 锁 |
| 旧 Scenario 包与未来 FDS 的关系不明确 | 两个旧合成包可无修改地生成“兼容但有限制”的 FDS 输入报告 |
| 非法层级、循环、缺失依赖或私有内容污染缺少统一机器结果 | 非法组合无部分锁，并返回稳定错误码、路径和顺序 |

## 用户可见变化

本阶段是契约型地基，没有新增页面。产品负责人可以通过 `make fds-owner-demo` 看到一个
真实生成的固定锁和一个真实拒绝结果，也可以直接查看以下生成制品：

- `contracts/fds/` 中的四类 Manifest Schema、组合 Schema、锁和兼容报告 Schema；
- 一个仅证明结构的多层合成图，以及一个非制造领域契约形状；
- 一个固定 DependencyLock，包含精确版本、来源、摘要、依赖边、权限和预算差量；
- 两个旧 Scenario fixture 的兼容报告，明确列出旧格式没有提供的 FDS 事实；
- 合法/非法组合、输入乱序、循环、冲突、公私边界、权限扩大和摘要篡改测试。

## 不可见地基

- 严格字段、版本和未知值拒绝规则，避免任意 JSON 被误当成合法领域包；
- 固定候选排序、最高兼容版本、回溯、拓扑顺序、错误顺序和摘要算法；
- 传递权限/预算只计算、不授权，以及公有 Domain 不能触达私有依赖的边界；
- 旧 Scenario 先走原校验器、保留摘要和历史语义且不补造许可/本体事实的适配层；
- Schema、锁、兼容报告连续导出、源码/wheel 依赖扫描和完整旧回归门。

## 目前看不见、也没有实现的成果

- 没有领域包市场、Registry、下载、安装、授权、发布、撤回或 Project DomainLock；
- 没有本体/术语注册、语义映射、知识上传/索引/RAG、Context Compiler 或 Grounding；
- 没有新的 API、数据库表、迁移、前端页面、模型调用、外部网络或真实数据；
- 没有钢帘线、排产、异常诊断业务实现，也没有跨行业真实 E2E；
- 没有企业签名根、发布者/许可批准、PostgreSQL、PREPROD/PROD 或业务 UAT。

因此，本阶段只证明“合同和锁的机器规则成立”，不证明“领域能力已经安装或运行”。

## 五分钟合法/非法包验证

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

这说明同一个解析器既能生成固定锁，也会在必需组件缺失时稳定拒绝，而且不会顺便
安装、授权或创建运行状态。完整工程验证命令为 `make epic-02-6a`；机器证据和限制见
`docs/acceptance/EPIC-02.6A-evidence.md`。

## 风险与限制

- 结果限定为 LOCAL_SYNTHETIC 契约工程；没有企业负责人签字，不能标为 `ACCEPTED`；
- `reference-domain-a` 只是第二领域形状，不是非制造真实 E2E，G5B 仍为 BLOCKED；
- 本地 SHA-256 attestation 不等于企业签名、发布者验证或许可证法律审查；
- Legacy Adapter 证明旧清单可无损进入兼容报告，不证明运行迁移、DomainLock 或 replay；
- 依赖规则已经能拦截明确结构化风险，但没有恶意内容/商业秘密扫描和撤回传播服务。

## 完成证据

- 需求与决策：`docs/requirements/EPIC-02.6A-fds-contract-kernel.md`、ADR-0006；
- 技术验收：40 个 FDS 聚焦测试、254 个全量 Python 测试、41 个独立 contract 测试，
  综合行/分支覆盖率 89.78%，4 个 Web 测试和 1 个浏览器 E2E；
- 供应链与运行回归：安全审计、源码/wheel 架构扫描、API/Web 重启冒烟、构建和 SBOM；
- 不可变证据：`docs/acceptance/generated-epic-02.6a-evidence.json` 绑定源码提交、锁文件、
  FDS 制品、两个旧 fixture、wheel、SBOM 和覆盖率摘要；
- 状态仍为 `REQ-FDS-001 = CLARIFYING / PARTIAL`，02.6B/02.6C 均为 `NOT_STARTED`。

## 下一步选择与真实前置条件

EPIC-02.6A 到此停止。进入 02.6B 前需要单独批准 Registry/Artifact/Project DomainLock
对象与生命周期、持久化/API 边界、组织私有可见性、发布者和企业签名责任人、撤回与
历史保留策略及对应安全评审。02.6C 还必须等待语义/知识 Owner、最小 competency
questions、授权查询与 Context Compiler 边界获批。二者都不能由本地契约测试自动视为
已完成。

建议产品负责人现在只做三个选择：确认 02.6A 的合同边界；为 02.6B 指定
Platform/Security/Artifact/Project Owner；决定是先补企业供应链前置，还是在这些 Owner
到位后另开 02.6B。不要在本任务中顺带启动 02.6B 或 02.6C。
