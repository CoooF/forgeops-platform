# EPIC-02.6A 产品负责人摘要

一句话结论：ForgeOps 现在能在本地、无网络、无数据库的条件下判断一个 FDS
组合是否合法，并为合法组合生成可重复的固定依赖锁；它还不是 FDS 运行平台。

## 前后对比

| 之前 | 现在 |
| --- | --- |
| 只有单个 Scenario Manifest，无法独立表达 Domain、组织覆盖层和组件 | 有严格的 Domain、Organization Overlay、Scenario、Component 四类契约 |
| 依赖版本、来源、摘要和传递权限没有统一固定锁 | 相同输入总是得到相同版本、拓扑顺序、权限/预算差量和 SHA-256 锁 |
| 旧 Scenario 包与未来 FDS 的关系不明确 | 两个旧合成包可无修改地生成“兼容但有限制”的 FDS 输入报告 |
| 非法层级、循环、缺失依赖或私有内容污染缺少统一机器结果 | 非法组合无部分锁，并返回稳定错误码、路径和顺序 |

## 能看见的成果

- `contracts/fds/` 中的四类 Manifest Schema、组合 Schema、锁和兼容报告 Schema；
- 一个仅证明结构的多层合成图，以及一个非制造领域契约形状；
- 一个固定 DependencyLock，包含精确版本、来源、摘要、依赖边、权限和预算差量；
- 两个旧 Scenario fixture 的兼容报告，明确列出旧格式没有提供的 FDS 事实；
- 合法/非法组合、输入乱序、循环、冲突、公私边界、权限扩大和摘要篡改测试。

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

## 下一步的真实前置条件

EPIC-02.6A 到此停止。进入 02.6B 前需要单独批准 Registry/Artifact/Project DomainLock
对象与生命周期、持久化/API 边界、组织私有可见性、发布者和企业签名责任人、撤回与
历史保留策略及对应安全评审。02.6C 还必须等待语义/知识 Owner、最小 competency
questions、授权查询与 Context Compiler 边界获批。二者都不能由本地契约测试自动视为
已完成。
