# ForgeOps 产品负责人进度总览

> 全项目状态：`PAUSED_ARCHIVED_BY_PRODUCT_OWNER`（2026-08-02）。封存标签：`forgeops-archive-2026-08-02-epic-02.7-partial`。各 Epic 的工程证据状态保留不变，但停止继续开发；EPIC-02.7 未最终验收，EPIC-03 未开始。详见[项目封存记录](../archive/PROJECT-ARCHIVE-2026-08-02.md)。

当前进度：EPIC-01、EPIC-02、EPIC-02.5 已完成本地合成工程验证；EPIC-02.6A 已达到
`VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING`，EPIC-02.6B 已达到
`VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING`；EPIC-02.6C 已达到
`VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING`。EPIC-02.7 已达到
`READY_FOR_PRODUCT_OWNER_REVIEW`，尚未最终接受。`REQ-FDS-001` 与 EPIC-02.6 整体
仍为 `CLARIFYING / PARTIAL`。企业 G0/G1/G2、真实数据、业务 UAT（业务用户验收测试）和
生产发布仍未通过。`LOCAL_SYNTHETIC` 表示只使用本地合成数据与受控测试身份；
DependencyLock 是固定依赖版本/来源/摘要的清单，Project DomainLock 是项目选定并固定的领域依赖清单。

`VERIFIED` 在本页只表示技术证据通过且说明准确；产品负责人尚未实际签字，因此没有任何一项是
`ACCEPTED`。目标环境也未发布，因此没有任何一项是 `RELEASED`。

| Epic | 大白话解释 | ForgeOps 现在多会了什么 | 产品负责人在哪里验证 | 用户可见程度 | 当前真实状态 | 明确未实现 | 解锁的下一阶段 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [EPIC-01](EPIC-01-owner-summary.md) | 有了一套稳定造产品、升级、重启和留证据的地基 | 可重复构建；检查健康；迁移本地数据结构；重启后保留状态；拒绝危险环境配置 | `make smoke`、`make migration-proof`、[历史 Evidence](EPIC-01-02-evidence.md) | 低：工程/运维入口，不是业务功能 | `VERIFIED`，仅 `LOCAL_SYNTHETIC_ENGINEERING` | Docker/PostgreSQL/Temporal 运行、备份恢复、企业环境、真实数据、业务能力、生产发布 | 可靠承载包契约、项目权限和后续运行时 |
| [EPIC-02](EPIC-02-owner-summary.md) | 开始知道能力包是什么，以及怎样安全进入和退出平台 | 校验、幂等安装、分步批准/授权/绑定/发布/启用、禁用/撤回/逻辑卸载并保留历史 | 包 API、窄范围契约测试、[历史 Evidence](EPIC-01-02-evidence.md) | 中低：API/证据可见，无独立包管理页 | `VERIFIED`，仅 `LOCAL_SYNTHETIC_ENGINEERING` | 排产/诊断业务、企业签名和制品库；安装不等于授权、绑定、发布或生产启用 | 真实 Project 绑定；旧 Scenario 向 FDS 的兼容演进 |
| [EPIC-02.5](EPIC-02.5-owner-summary.md) | 开始认识组织、工作空间、项目、成员和角色 | Owner 建层级和绑定包；Viewer 只读；Outsider 隔离；归档后阻止新写入并保留历史 | `make e2e` 驱动真实 Project Center；[Evidence](EPIC-02.5-evidence.md) | 高：已有真实 Project Center 页面 | `VERIFIED_FOR_LOCAL_SYNTHETIC_ENGINEERING` | 企业登录/目录/策略、PostgreSQL 隔离、真实组织数据、业务 UAT、生产权限 | 各领域分别落在不同 Project；为 Project DomainLock 提供范围 |
| [EPIC-02.6A](EPIC-02.6A-owner-summary.md) | 有了描述领域资源包和固定依赖清单的统一语法 | 合法多层包生成固定 DependencyLock；乱序不变；循环、缺失、冲突、私有依赖和权限扩大稳定拒绝 | `make fds-owner-demo`、`contracts/fds/`、[Evidence](EPIC-02.6A-evidence.md) | 中低：CLI/固定制品可见；后续 02.6B 页面不改变本行证据边界 | `VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING`；`REQ-FDS-001` 仍 `CLARIFYING / PARTIAL` | 02.6A 本身未实现 Registry、安装、Project DomainLock、语义查询、知识检索或 Context Compiler；其中 Registry/DomainLock 已由独立 02.6B 交付 | 已由独立 02.6B 接续 Registry 治理；仍未自动批准 02.6C |
| [EPIC-02.6B](EPIC-02.6B-owner-summary.md) | 把领域包登记、组织安装、项目固定版本和撤回影响变成真实治理能力 | 四类版本入 Registry；组织保存固定 DependencyLock；Project 创建/切换不可变 DomainLock；撤回定位影响并阻止新使用 | Domain Registry 页面、Project Center 的 DomainLock 面板、`make epic-02-6b-owner-demo`、`make e2e`、[Evidence](EPIC-02.6B-evidence.md) | 高：真实页面/API/数据库可操作 | `VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING`；`REQ-FDS-001` 与 EPIC-02.6 仍 `CLARIFYING / PARTIAL` | 企业签名/许可/制品、PostgreSQL 服务运行、工作流/Agent、Run/replay、真实数据和业务 UAT；本行 B 本身不包含后续 C | 02.6C 已通过独立本地验证；本行不因后续证据扩大 B 的验收边界 |
| [EPIC-02.6C](EPIC-02.6C-owner-summary.md) | 让锁定版本的语义/知识可查、可按预算编译、可结构化校验，又不靠大模型猜 | 唯一/歧义/未知不猜；KnowledgeAsset 版本治理；确定 ContextManifest；Grounding 和 v1/v2 影响 | Semantic & Knowledge 页、Project Context 面板、`make epic-02-6c-owner-demo`、[Evidence](EPIC-02.6C-evidence.md) | 高：真实页面/API/数据库可操作 | `VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING`；REQ-SEM/KNW/GRD 与 EPIC-02.6 仍 `CLARIFYING / PARTIAL` | 行业本体、Agent/LLM/RAG、Workflow/Run/画布、企业许可/签名、真实数据、UAT/PROD | 仅具备提请 EPIC-02.7 UI/UX 原型评审的条件，不自动开始 |
| [EPIC-02.7](EPIC-02.7-owner-summary.md) | 把验收后台重构为可走查的 ForgeOps 产品结构，并在真实执行前冻结画布、Agent、运行与证据体验 | 方向 A Shell；工作流画布；三个节点级 Skill/MCP 执行 Agent；协调型主 Agent；Run/候选/Evidence；数据、领域与治理连续入口 | `/design-preview/prototype`、`make epic-02-7`、`make e2e`、[Evidence](EPIC-02.7-evidence.md) | 高：完整高保真本地交互原型；真实 API 页面仍独立可用 | `READY_FOR_PRODUCT_OWNER_REVIEW`；产品负责人尚未最终接受 | 所有 Workflow/Run/Agent/Skill/MCP 后端、真实执行、真实数据、企业环境和 UAT | 只有最终明确验收后，才可另行生成 EPIC-03 提示词；当前不得进入 |

所有验证只使用本地合成数据和受控本地身份。详细的五分钟成功与拒绝路径、风险边界、需求、
Evidence 和提交哈希请进入每行的 Owner Summary。
