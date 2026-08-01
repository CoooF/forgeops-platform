# EPIC-02.6B 产品负责人摘要

状态：`VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING`；`REQ-FDS-001` 与 EPIC-02.6
整体仍为 `CLARIFYING / PARTIAL`。这不是企业供应链验收、FDS Runtime、业务验收或生产发布。

## 一句话结论

ForgeOps 现在能把四类固定 FDS 包真实登记到 Registry，为组织解析并安装不可变依赖锁，让
Project 固定、切换和追查自己的 DomainLock，并在依赖撤回后指出受影响对象、阻止新的使用。

## 为什么要做

EPIC-02.6A 只回答“这组 Manifest 能否合法、确定地组合”，还不能回答资产登记在哪里、哪个组织
可以安装、某个 Project 选了哪份版本、升级后旧选择如何调查，或撤回一个传递依赖会影响谁。
02.6B 把这层产品治理落到真实 API、数据库与页面，同时继续把安装、授权、运行和语义能力分开。

## 前后对比

| 开发前 | 开发后 |
| --- | --- |
| FDS 只有本地契约/解析器，没有 Registry | 四类固定版本严格、幂等登记，Manifest 与摘要不可原地修改，治理状态单独留痕 |
| 组织不能从 Registry 安装领域组合 | 组织从可见、可用 Registry 候选解析并原子保存 `INSTALLED_DISABLED` Installation 与精确 DependencyLock |
| Project 没有领域版本选择 | ACTIVE Project 最多一个 current DomainLock；切换创建新锁，旧锁变为 SUPERSEDED 且内容仍可读 |
| 撤回影响只能人工猜测 | 直接/传递引用索引列出受影响 Installation/Project 锁，旧历史不改写，新安装/新锁被阻断 |
| 无真实管理入口 | Domain Registry 页面与 Project Center 的 DomainLock 面板均走真实 API/数据库，并有真实浏览器 E2E |

## 用户可见页面和操作

- Web Shell 顶层 **Domain Registry**：筛选可见包版本，查看不可变事实、依赖、权限/预算与本地
  信任边界；注册合成 Manifest；预览/创建组织 Installation；按权限 quarantine、withdraw 或改变
  Installation 生命周期，并查看影响摘要。
- Project Center 的 **DomainLock** 面板：查看 current 锁、健康、节点和摘要；从本组织有效
  Installation 预览结构化差异并切换；读取不可变 SUPERSEDED 历史。
- Project Viewer 只读 current 摘要，不能读取历史或治理；Outsider 统一不可发现；归档 Project
  不能创建或切换锁。
- 页面始终显示 `LOCAL_SYNTHETIC`、`NOT_ENTERPRISE_VERIFIED`、
  `authorizationEffect=NONE`、`semanticRuntimeReady=false`、
  `runtimeBindingCreated=false`，不会把“选择了版本”说成“已经运行”。

真实页面启动和操作见 [本地运行手册](../runbooks/local-development.md)。

## 不可见地基

- `platform_core.domain_registry` 保持领域中立；`fds_sdk` 仍是无 API/SQL/身份反向依赖的纯契约层；
- Alembic `0006` 增加 Registry、Installation、引用索引、ProjectDomainLock、幂等记录和数据库层
  current 唯一约束，无物理删除级联；
- 所有候选只从当前主体可见 Registry 读取，并重新验证摘要、状态、组织私有 Scope 和依赖锁；
- 锁切换在一个事务里创建新锁并 supersede 旧锁；成功写入与允许审计同事务提交；既有拒绝审计
  仍受旧 Audit Repository 独立事务限制，已在 ADR 记录；
- 固定引用表让撤回影响不依赖模糊 JSON 搜索；派生健康不改写历史锁；
- 写 API 使用 `Idempotency-Key`，治理状态使用 `If-Match`，跨 Scope 详情统一 404；
- FDS Scenario Descriptor 可登记调查，但不会创建或替代既有 Scenario Installation/Binding 真值。

## 五分钟成功与拒绝验证

在仓库根目录运行：

```bash
make epic-02-6b-owner-demo
```

应看到：3 个 Registry 版本、2 个 `INSTALLED_DISABLED` Installation；第一次 Project 锁变为
`SUPERSEDED`，第二次仍为 `CURRENT`，历史数为 2 且重启后仍存在；Viewer current 为 200、历史
为 404，Outsider 为 404；撤回传递 Component 后影响为 2 个 Installation 和 2 个 Project 锁，
current 健康为 `AT_RISK`，新锁稳定返回 409 `WITHDRAWN_OR_QUARANTINED_DEPENDENCY`。

真实页面/API 成功与拒绝链路运行：

```bash
make e2e
```

Playwright 会从页面注册两个 Domain 版本、创建两个 Installation、创建并切换 DomainLock、刷新后
读取历史、以 Viewer 验证只读，再撤回传递依赖并确认影响和新锁阻断。它不是前端 Mock。

## 明确未实现和不得对外宣称

- 没有 Ontology/Terminology/Mapping、语义查询、Constraint、Grounding、Knowledge/RAG 或
  Context Compiler；EPIC-02.6C 未开始；
- 没有 WorkflowDefinition、Run/replay、Temporal、Agent/模型/MCP/Skill 运行；EPIC-03 未开始；
- Installation/DomainLock 没有创建 Entitlement、Grant、Scenario Binding、Release、Secret、网络权限、
  Worker 或外部动作；
- 没有远程 Artifact 下载、企业签名根、发布者/许可法律审核或恶意内容扫描；
- 没有 PostgreSQL 服务级运行、企业 OIDC/SCIM、PREPROD/PROD、真实数据或业务 UAT；
- 没有参考场景业务、钢帘线排产、设备诊断或跨行业真实 E2E；G2/G4/G5A/G5B 未提升。

## 风险与限制

- 证据使用 SQLite、受控本地身份、合成 Manifest 和 `local-sha256`；它只证明本地工程完整性；
- 当前成功状态与允许审计共享事务，但拒绝审计沿用独立 append-only Audit Repository；进程在拒绝
  决策与审计写入之间崩溃仍可能丢失拒绝证据，生产前需统一 UoW/Outbox；
- 未进行 PostgreSQL partial-index 并发服务级压测；数据库约束、事务和篡改/双 current 负例已在
  SQLite 与生成 SQL 路径验证；
- 撤回只标记派生风险并阻止新使用，不自动换版、不改旧锁、不撤销从未创建的 Grant；
- `TEST-FDS-002` 只增加 Registry/DomainLock 子证据，历史 Run/replay 仍未验证；
- `TEST-FDS-004` 企业供应链仍为 `NOT_STARTED / BLOCKED`。

## 完成证据：需求、测试、Evidence 和提交

| 项目 | 对应内容 |
| --- | --- |
| 需求 | [EPIC-02.6B 需求](../requirements/EPIC-02.6B-fds-registry-project-domain-lock.md)；`REQ-FDS-001` 仍 `CLARIFYING / PARTIAL` |
| 决策 | [ADR-0007](../adrs/0007-fds-registry-installation-project-domain-lock.md) |
| 关键测试 | `TEST-FDS-REGISTRY-001`、`TEST-FDS-REGISTRY-SCOPE-001`、`TEST-FDS-INSTALL-001/NEG-001`、`TEST-FDS-DOMAINLOCK-001/NEG-001`、`TEST-FDS-IMPACT-001`、`TEST-FDS-AUTH-001`、`TEST-FDS-API-001`、`TEST-FDS-PERSISTENCE-001`、`TEST-FDS-LEGACY-002`、`TEST-WEB-FDS-001`、`TEST-ARCH-004` |
| 人读证据 | [EPIC-02.6B Evidence](EPIC-02.6B-evidence.md) |
| 机器证据 | `generated-epic-02.6b-evidence.json`（在独立证据提交后绑定并记录摘要） |
| 验证源码提交 | 在最终验证后记录 |
| 证据提交 | 在机器证据生成后记录 |

最终验证已通过 341 个 Python 测试、41 个独立契约测试、6 个 Web 测试、40 个 02.6A 聚焦
测试、63 个 02.6B 聚焦测试和 2 个真实浏览器 E2E，综合行/分支覆盖率 88.34%；源码/证据
提交与机器证据摘要将在 clean verified source commit 后写回，不会预填未来哈希。

## 是否具备进入 EPIC-02.6C 的条件

02.6B 只把“固定资产、安装和 Project 选择”变成了可靠前置，因此具备**单独评审** 02.6C 的
技术入口，但没有自动批准继续。开始 02.6C 前仍需产品负责人指定 Semantic/Knowledge/Grounding
Owner、最小 competency questions、授权查询/数据分类边界、KnowledgeAsset 保留与删除策略、
Grounding 证据契约及独立验收门。本任务到此停止，不进入 02.6C、EPIC-03 或参考场景业务。
