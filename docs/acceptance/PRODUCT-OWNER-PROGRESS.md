# ForgeOps 产品负责人进度总览

当前进度：EPIC-01、EPIC-02、EPIC-02.5 已完成本地合成工程验证；EPIC-02.6A 已按本任务
最终证据达到 `VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING`，但 `REQ-FDS-001`
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
| [EPIC-02.6A](EPIC-02.6A-owner-summary.md) | 有了描述领域资源包和固定依赖清单的统一语法 | 合法多层包生成固定 DependencyLock；乱序不变；循环、缺失、冲突、私有依赖和权限扩大稳定拒绝 | `make fds-owner-demo`、`contracts/fds/`、[Evidence](EPIC-02.6A-evidence.md) | 中低：CLI/固定制品可见，无管理页面 | `VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING`；`REQ-FDS-001` 仍 `CLARIFYING / PARTIAL` | Registry、安装 API、Project DomainLock、语义查询、知识检索、Context Compiler；02.6B/02.6C 未启动 | 具备单独评审 02.6B 契约/治理前置的条件，未自动批准继续 |

所有验证只使用本地合成数据和受控本地身份。详细的五分钟成功与拒绝路径、风险边界、需求、
Evidence 和提交哈希请进入每行的 Owner Summary。
