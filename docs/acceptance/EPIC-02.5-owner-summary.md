# EPIC-02.5 产品负责人摘要

状态：`VERIFIED_FOR_LOCAL_SYNTHETIC_ENGINEERING`。这里的身份和数据都是本地合成的，
不是企业登录、真实组织目录或生产权限。

## 一句话结论

ForgeOps 开始认识组织、工作空间、项目、成员和角色，并能把每个人限制在自己获准的项目范围内。

## 为什么要做

Organization（组织，即业务或企业边界）、Workspace（工作空间，即组织下的一组协作范围）、
Project（项目，即具体工作的权限和生命周期边界）如果不存在，钢帘线排产、设备诊断等后续能力
就只能混在同一个全局空间里。这样既无法分开负责人和数据范围，也容易让旁观者修改项目或让
外部人员发现不属于自己的资源。

## 前后对比

| 开发前 | 开发后 |
| --- | --- |
| 包和操作只有全局或任意字符串范围 | 有稳定的 Organization → Workspace → Project 层级和真实 Project ID |
| 一个请求头可能被误解为授权 | 本地请求头只识别受控测试身份；持久化成员关系和角色才决定权限 |
| 不能清楚区分 Owner、Editor、Viewer 和 Outsider | RBAC（按角色分配权限）与范围继承默认拒绝，跨组织不继承 |
| 项目关闭后如何保留历史不明确 | 归档项目阻止修改和新绑定，但项目、成员、绑定与审计历史仍可读 |
| 没有可操作的项目入口 | Project Center 使用真实 API（程序调用入口）展示层级、生命周期、成员、包和审计 |

## 用户可见变化：现在能做什么、在哪里看

用户现在可以在 Project Center（项目中心页面）中：

- 以本地 Owner 创建 Organization、Workspace 和 Project，激活或归档 Project；
- 查看和管理成员、角色、可绑定包、绑定记录和项目审计；
- 把一个已经测试、批准且授予所需权限的合成 Scenario Package 绑定到真实 Project；
- 切换到 Viewer 查看只读状态，切换到 Outsider 确认其他项目不会出现在列表中；
- 刷新页面后继续读取 API 持久化状态，而不是得到浏览器内的假成功。

本地直接运行时入口是 `http://127.0.0.1:5173/` 的 `Project Center`；真实 API 位于
`/v1/organizations`、`/v1/workspaces/{id}`、`/v1/projects/{id}`、成员、包绑定和审计路由。

## 不可见地基

- Principal（主体，即系统识别到的人）、Membership（成员关系）和角色/权限矩阵；
- 可替换 AuthPort（身份来源接口）与集中式授权服务，认证和授权明确分离；
- Organization、Workspace、Project、Membership 和 ProjectPackageBinding 的持久化与迁移；
- 默认拒绝、跨范围隐藏、禁用主体/暂停或撤回成员关系的即时生效；
- 创建幂等（同一请求重试不会重复创建）、版本冲突保护、最后一个组织 Owner 保护和追加式授权审计；
- 归档而非物理删除，保证历史调查和后续 Evidence 可以继续引用原项目。

## 五分钟验证路径

在仓库根目录运行：

```bash
make e2e
```

该命令会启动真实本地 API 和 Project Center，并让真实浏览器自动完成固定合成路径：

1. `local-owner` 创建 Organization → Workspace → Project；
2. 一个合法合成包经 API 完成测试、批准和权限授予后，在 Project Center 中被绑定；
3. `local-viewer` 仍能看项目，但看不到编辑、添加成员和绑定按钮；
4. `local-outsider` 看不到该组织和项目；
5. Owner 归档项目后，新绑定请求返回 `409 / ILLEGAL_STATE_TRANSITION`，刷新后仍保持归档；
6. 终端最终显示 1 个 Playwright（真实浏览器自动化）用例通过。

这条路径使用真实页面、真实 API 和本地数据库，不是组件 Mock 或截图。它仍只是
`LOCAL_SYNTHETIC` 身份演示，浏览器验证完成后服务会自动停止。

## 成功案例

Owner 创建 `Synthetic Operations` 组织、`Advisory Lab` 工作空间和 `Evidence Project`
项目，把已经批准的 `steel-cord-scheduling` 合成包绑定到该项目；页面显示绑定成功，刷新后项目
状态仍在。钢帘线名称只标识 fixture，不表示排产已经实现。

## 拒绝或越权案例

- Viewer 可以查看项目，但不能编辑、归档、添加成员或绑定包；
- Outsider 的组织选择器显示无可见组织，不能通过资源发现接口看到别人的项目；
- 项目归档后，即使 Owner 仍有角色，新绑定也以 `ILLEGAL_STATE_TRANSITION` 被拒绝；
- 未知、伪造或禁用主体，以及暂停/撤回的成员关系，在下一次请求即失去访问能力。

## 明确未实现和不得对外宣称

- 当前不是企业 OIDC/SCIM（企业登录和目录同步协议）登录，没有密码、邀请、企业目录或正式账号生命周期；
- 项目包绑定不等于包授权、环境发布、启用、数据访问或业务运行；
- 没有钢帘线排产、设备诊断、FDS（领域资源契约）、语义/知识或工作流运行时；
- 没有 PostgreSQL（目标数据库）服务级隔离、数据库 RLS（按数据行隔离权限）、企业策略发布/
  回滚或独立安全审查；
- 没有真实数据、企业浏览器/设备矩阵、性能/无障碍认证、PREPROD/PROD 或业务 UAT。

## 风险与限制

- `X-ForgeOps-Actor` 只在 DEV/TEST 选择受控本地主体，本身不授予任何权限；
- `local-owner`、`local-viewer`、`local-outsider` 都是 `LOCAL_SYNTHETIC` 身份，不是企业员工登录；
- SQLite 和本机 Chrome 的通过结果不能证明企业数据库、SSO、设备和网络条件；
- 跨范围隐藏采用统一 `RESOURCE_NOT_FOUND`，能降低资源枚举风险，但尚未经过企业渗透测试；
- 企业 G0/G1/G2、真实数据、业务 UAT、PREPROD/PROD 和生产发布仍未通过。

## 完成证据：需求、测试、Evidence 和提交

| 项目 | 对应内容 |
| --- | --- |
| 需求 | [EPIC-02.5 需求](../requirements/EPIC-02.5-identity-project-scope.md)；`REQ-IAM-001`、`REQ-POL-001`、`REQ-PKG-001`、`REQ-OPS-001` |
| 决策 | [ADR-0005](../adrs/0005-local-identity-project-boundary.md) |
| 关键测试 | `TEST-IAM-POLICY-001`、`TEST-IAM-AUTH-001`、`TEST-IAM-ISOLATION-001`、`TEST-IAM-MEMBERSHIP-001`、`TEST-PKG-PROJECT-BINDING-001`、`TEST-WEB-PROJECT-E2E-001` |
| 人读证据 | [EPIC-02.5 Evidence](EPIC-02.5-evidence.md) |
| 机器证据 | [generated-epic-02.5-evidence.json](generated-epic-02.5-evidence.json) |
| 实现提交 | `c2d4384daa8421ebae7ff27b6b1a444594233476` |
| 最终验证源码 | `18bee65b20689068d6dd29f485133b9129c60385` |
| 证据提交 | `806978e0bda0a56e0b8caf010af6de1d4d30c3ad` |

Evidence 记录了 214 个 Python 测试、160 个权限/范围专项用例、4 个 Web 测试和 1 个浏览器
E2E，以及迁移、重启、安全、架构和 SBOM 结果；这些数字不替代企业身份验收。

## 下一步选择与产品负责人决策

本阶段让钢帘线排产、设备诊断或其他领域以后可以分别属于不同 Project，也为 FDS 的
Project DomainLock（项目固定领域依赖清单）提供了真实项目边界。产品负责人现在无需修改本地已验证结论；若要进入企业
身份与项目治理，必须指定 Identity/Security/Project Owner，批准 OIDC/SCIM、策略发布、组织模型、
数据库隔离和企业 UAT。FDS Registry 与 Project DomainLock 属于后续 02.6B，未在本阶段启动。
