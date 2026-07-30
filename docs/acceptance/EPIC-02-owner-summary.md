# EPIC-02 产品负责人摘要

状态：`VERIFIED_FOR_LOCAL_SYNTHETIC_ENGINEERING`。这里的“已验证”只覆盖本地合成包契约和
生命周期，不代表企业供应链验收、业务能力实现或生产启用。

## 一句话结论

ForgeOps 开始知道“能力包是什么”，并能校验、安装、禁用、撤回和保留历史。

## 为什么要做

Scenario Package（场景包，即可安装的场景能力契约包）如果没有统一说明书和受控生命周期，
任何文件都可能冒充能力，安装动作可能被误当成授权或上线，出问题后也无法撤回并调查历史。
EPIC-02 先建立可信的包入口和状态规则，避免后续业务能力以不可追踪方式进入平台。

## 前后对比

| 开发前 | 开发后 |
| --- | --- |
| 平台不知道一个场景包应声明什么 | Scenario Manifest（包说明书）严格声明版本、制品摘要、权限、预算、兼容范围和各类 Pack |
| 包内容、版本和权限错误缺少统一拒绝原因 | 缺字段、摘要错误、未知权限、版本不兼容和破坏性变更都有稳定错误码 |
| “安装”容易被混同为“可运行” | 幂等安装（重复提交也只保留一条记录）、测试、批准、授权、绑定、环境发布和启用是分开的状态与记录 |
| 禁用、撤回或卸载可能丢失调查线索 | 新运行被阻止，但 Manifest、安装记录和审计历史继续保留 |
| 场景实现可能反向污染平台核心 | 固定依赖方向为“场景包 → SDK → 平台契约”，源码和制品扫描可验证 |

## 用户可见变化：现在能做什么、在哪里看

本阶段没有独立的包管理页面。产品/工程人员可以通过真实 API（程序调用入口）或固定契约测试：

- 调用 `POST /v1/scenario-packages:validate` 校验包说明书和制品；
- 调用 `POST /v1/scenario-package-installations` 安装合法包，并通过
  `GET /v1/scenario-package-installations` 查看安装历史；
- 分别执行测试、批准、权限授予、绑定、环境发布、启用、禁用、撤回和逻辑卸载；
- 通过 `/v1/audit-events` 调查生命周期记录，通过运行资格接口确认新运行是否被阻止；
- 在 [EPIC-01/02 Evidence](EPIC-01-02-evidence.md) 和
  [机器证据](generated-verification-evidence.json) 查看固定结果和边界。

安装只表示平台保存并识别了合法包；它不等于授权、项目绑定、环境发布、生产启用或业务有效。

## 不可见地基

- 严格 Manifest、DomainSchema 和各类 Pack（包内的结构化能力声明）契约；
- SDK（场景开发工具契约）兼容范围、Schema（结构规则）兼容、权限白名单和资源预算校验；
- 安装与环境发布分离的状态机、幂等安装、稳定错误码和追加式审计；
- 禁用、撤回和逻辑卸载只阻止新的使用，不物理抹掉历史；
- 六个通用 Port（平台与未来实现之间的标准接口）和隔离 Worker（独立执行进程）制品边界；
- 声明式 UI（用户界面）扩展，不允许第三方 JavaScript 在页面进程中任意执行。

## 五分钟验证路径

在仓库根目录运行这组窄范围契约验证，无需启动完整环境或阅读源代码：

```bash
uv run pytest -q \
  tests/contract/test_manifest_validation.py \
  tests/contract/test_package_service.py
```

期望结果：所有选定用例通过。成功路径会接受仓库中的两个合法合成包，并证明一个包只有依次
完成测试、批准、授权、绑定、发布和启用后才允许新的本地 TEST 运行。失败路径会确认摘要篡改、
签名错误、未知权限、不兼容 SDK 版本、缺少授权/绑定和非法卸载顺序均被拒绝。

这是真实 Scenario SDK 和包生命周期服务的验证，不是排产或诊断业务演示。需要观察持久化 API
时可另运行 `make smoke`；历史已验证结果见 Evidence，不必为阅读本文重新运行全量 `make verify`。

## 成功案例

合法的 `steel-cord-scheduling` 合成包通过 Manifest 与制品摘要校验后可以幂等安装；重复安装不会
制造第二条记录。完成 TEST 环境的测试、批准、权限授予、绑定、发布和启用后，运行资格检查返回
允许。包名只是契约 fixture（固定合成样例），不代表钢帘线排产业务已经实现。

## 拒绝或失败案例

把制品内容改成 `tampered` 会得到 `ARTIFACT_DIGEST_MISMATCH`；声明未知权限会得到
`UNKNOWN_PERMISSION`；要求不兼容 SDK 会得到 `SDK_INCOMPATIBLE`。刚安装的包仍是
`INSTALLED_DISABLED`，未授权或未绑定时不能发布，未先禁用/撤回时不能逻辑卸载。

## 明确未实现和不得对外宣称

- Scenario Package 只是可安装契约，不是排产、设备诊断、仿真或 Agent 业务实现；
- 安装不等于授权、Project 绑定、发布、启用、业务验收或生产运行；
- 没有企业制品库、企业签名根、发布者验证、许可证法律审查或恶意内容扫描；
- 没有动态第三方插件执行、外部模型调用、真实数据接入或外部系统写入；
- 没有证明 PostgreSQL/Temporal 容器运行、PREPROD/PROD 或企业撤回传播。

## 风险与限制

- 两个参考包都是 `FIRST_PARTY_LOCAL` 的合成契约 fixture，不含真实或脱敏企业数据；
- 本地 SHA-256 摘要校验不是企业数字签名或供应链批准；
- LOCAL_SYNTHETIC 测试身份和 SQLite 证据不能代替企业登录、企业策略和 PostgreSQL；
- Advisory Mode 只允许记录未执行建议，PREPROD/PROD 继续固定 DenyAll；
- 企业 G0/G1/G2、真实业务 UAT、业务价值和生产发布均未通过。

## 完成证据：需求、测试、Evidence 和提交

| 项目 | 对应内容 |
| --- | --- |
| 产品范围 | [产品路线图中的 EPIC-02](../../../docs/production-baseline/01-product-scope-and-roadmap.md) |
| 需求 | `REQ-PKG-001`、`REQ-SDK-001`、`REQ-ACT-001` 的本地工程子范围 |
| 决策 | [ADR-0002](../adrs/0002-core-scenario-separation.md)、[ADR-0003](../adrs/0003-package-trust-lifecycle.md) |
| 关键测试 | `TEST-DOM-001`、`TEST-SCHEMA-001`、`TEST-CONTRACT-001`、`TEST-SDK-001/002`、`TEST-ACT-001/002`、`TEST-ARCH-001` |
| 人读证据 | [EPIC-01/02 Evidence](EPIC-01-02-evidence.md) |
| 机器证据 | [generated-verification-evidence.json](generated-verification-evidence.json) |
| 源码提交 | `5474f948abd31f5d3856315e1c95ef819fa732bb` |
| 证据提交 | `385d0dfe6f870b4024dcdcb04a21fd703ee5c1ae` |

历史证据记录 17 个独立契约测试以及构建、安全、架构、迁移、API 重启和固定导出结果；数字只
说明本地工程门，不把两个 fixture 提升为业务能力。

## 下一步选择与产品负责人决策

本阶段解锁了 EPIC-02.5 可以把已批准包绑定到真实 Project，也为 EPIC-02.6A 复用旧 Scenario
契约提供了兼容输入。产品负责人现在无需改变本地 EPIC-02 状态；若要进入企业包治理，需要另行
决定发布者、签名根、制品库、许可证、安全扫描、撤回响应和生产授权责任。当前不能标记
`ACCEPTED` 或 `RELEASED`。
