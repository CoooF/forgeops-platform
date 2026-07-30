# EPIC-01 产品负责人摘要

状态：`VERIFIED_FOR_LOCAL_SYNTHETIC_ENGINEERING`。这里的“已验证”只指本地合成工程，
不等于产品负责人验收、企业环境通过或生产发布。

## 一句话结论

ForgeOps 有了可以稳定开发、构建、测试、升级数据结构、重启并留存证据的工程地基。

## 为什么要做

没有这层地基，同一份代码可能在不同电脑上得到不同结果，数据库升级可能破坏已有状态，
服务“能启动”也可能只是空壳，后续每个业务功能都无法证明自己可重复、可恢复、可追踪。
EPIC-01 先让团队能可靠地造产品和判断系统是否健康，再承载包、项目、工作流等能力。

## 前后对比

| 开发前 | 开发后 |
| --- | --- |
| 没有独立、可重复构建的 ForgeOps 仓库 | 有独立仓库、锁定依赖和固定质量门 |
| 无法证明数据库结构升级和回退可重复 | 本地 SQLite（轻量文件数据库）迁移可往返，服务能识别数据库是否已升级 |
| 服务重启后状态是否保留不确定 | 独立 API（程序调用入口）双启动后，已写入的包安装记录仍可读取 |
| 健康、日志、指标、审计和制品证据没有统一入口 | 有健康接口、结构化日志、Trace（一次请求的追踪编号）、Metric（运行指标）、审计和机器证据 |
| 错误环境可能误开外部动作能力 | 本地只记录建议，较高环境固定拒绝危险配置和外部执行 |

## 用户可见变化：现在能做什么、在哪里看

EPIC-01 不是终端用户功能，也没有为它制造产品页面。开发和运维人员现在可以：

- 通过 `/health/live` 看进程是否存活，通过 `/health/ready` 看数据库是否已迁移并可用；
- 通过 `/v1/platform/status` 看见 `LOCAL_SYNTHETIC_ENGINEERING`、仅合成数据、无企业批准等真实边界；
- 用 `make smoke` 验证 API 重启后状态仍在，用 `make migration-proof` 验证数据库结构升级与回退；
- 在 [EPIC-01/02 Evidence](EPIC-01-02-evidence.md) 和
  [机器证据](generated-verification-evidence.json) 中查看当时的命令、结果、源码提交和限制。

## 不可见地基

- Python、TypeScript 工作区和依赖版本已锁定，格式、类型、测试和构建有统一入口；
- API、文件持久化、内容寻址对象存储替身、追加式审计、日志、追踪和指标骨架已建立；
- 数据库迁移脚本（按版本升级数据结构的步骤）和本地重启验证已建立；
- SBOM（软件物料清单，即软件依赖清单）、依赖安全扫描、架构扫描和 CI（自动质量门）已建立；
- Advisory Mode（只生成或记录建议、不执行外部动作）与 DenyAll（无条件拒绝外部动作）
  的环境边界已固定。

## 五分钟验证路径

在仓库根目录使用现有本地合成环境：

```bash
make smoke
make migration-proof
uv run pytest -q tests/unit/test_config.py tests/unit/test_action_boundary.py
```

期望结果：

1. `make smoke` 等待真实 `/health/ready` 成功，启动 API、写入状态、停止并再次启动，最终输出
   `passed: true` 和持久化成功；输出中的 Project 持久化是后续 EPIC-02.5 的回归项；
2. `make migration-proof` 完成当前迁移头的升级、回退和再升级；EPIC-01 的历史证据头为 `0004`，
   当前仓库因 EPIC-02.5 已自然演进到 `0005`；
3. 两个窄范围负面测试文件通过，表示不安全配置和外部执行尝试被稳定拒绝。

这条路径使用真实 API 进程和本地持久化，不是前端伪造成功状态。不得对共享或企业数据库执行
迁移回退；上述命令只用于仓库配置的独立本地数据库。

## 成功案例

一个合法合成包被写入本地数据库后，API 进程停止并重新启动，安装记录仍然可读；健康检查同时
确认数据库已经迁移。这证明基础设施能够保存真实后端状态，而不是只在内存里演示一次。

## 拒绝或失败案例

当 PREPROD/PROD（预生产/生产环境）尝试使用 Mock（只记录、不执行的本地动作替身）或本地
SQLite 时，配置在
启动阶段即被拒绝；DenyAll 适配器收到任何动作提案都会返回
`ACTION_EXECUTION_DENIED` 并写入审计。错误配置不会被静默降级成“看起来能跑”。

## 明确未实现和不得对外宣称

- 不能宣称 ForgeOps 已有排产、设备诊断、工作流运行或其他用户业务功能；
- 不能宣称 Docker Compose 中的 PostgreSQL（目标数据库）、Temporal（持久工作流引擎）、
  MinIO（对象存储）和 OpenTelemetry（观测采集）服务已运行验证；
- 不能宣称备份恢复、灾难恢复、发布回滚、负载、故障注入或远程 CI 已通过；
- 不能宣称已接入企业登录、Secret、网络、制品签名、真实数据或生产环境；
- 不能把“有 React 状态页和健康接口”说成产品已上线。

## 风险与限制

- 数据范围是 `LOCAL_SYNTHETIC`，即只使用本地合成数据；没有真实或脱敏企业数据；
- SQLite 是直接运行替身，不是 PostgreSQL 生产证据；Docker、PostgreSQL 和 Temporal 仅有代码/
  配置骨架，状态为 `CODE_COMPLETE` 或未验证；
- 企业 G0/G1/G2、业务 UAT（业务用户验收测试）、PREPROD、PROD 均未通过；
- 本地安全扫描只证明当时的源码和锁文件结果，不能替代企业安全评审和持续漏洞运营。

## 完成证据：需求、测试、Evidence 和提交

| 项目 | 对应内容 |
| --- | --- |
| 产品范围 | [产品路线图中的 EPIC-01](../../../docs/production-baseline/01-product-scope-and-roadmap.md) |
| 需求 | `REQ-OPS-001`、`REQ-ACT-001` 的本地工程子范围 |
| 决策 | [ADR-0001](../adrs/0001-independent-local-repository.md)、[ADR-0004](../adrs/0004-persistence-and-local-services.md) |
| 关键测试 | `TEST-BUILD-001`、`TEST-OPS-MIGRATION-001`、`TEST-OPS-API-SMOKE-001`、`TEST-OPS-WEB-SMOKE-001`、`TEST-SBOM-001`、`TEST-ACT-001/002` |
| 人读证据 | [EPIC-01/02 Evidence](EPIC-01-02-evidence.md) |
| 机器证据 | [generated-verification-evidence.json](generated-verification-evidence.json) |
| 源码提交 | `5474f948abd31f5d3856315e1c95ef819fa732bb` |
| 证据提交 | `385d0dfe6f870b4024dcdcb04a21fd703ee5c1ae` |

历史结果为 49 个 Python 测试、17 个独立契约测试、2 个 Web 测试、94.09% 综合行/分支
覆盖率；这些数字只辅助说明工程门通过，不单独代表产品验收。

## 下一步选择与产品负责人决策

本阶段解锁了 EPIC-02 的包契约、EPIC-02.5 的项目与权限，以及后续运行时可以复用的构建、
迁移、健康和证据路径。产品负责人现在无需为本地 EPIC-01 追加功能决策；若要提升到企业
`VERIFIED` 或继续发布准备，必须另行决定企业部署拓扑、PostgreSQL/Temporal 验证环境、
安全与运维负责人、真实 NFR（非功能指标）和验收人。当前不能标记 `ACCEPTED` 或 `RELEASED`。
