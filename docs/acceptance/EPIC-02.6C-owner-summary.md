# EPIC-02.6C 产品负责人摘要

状态：`VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING`。该 VERIFIED 只限本地合成、无模型的 02.6C 薄切片；REQ-SEM/KNW/GRD 与 EPIC-02.6 整体仍是 `CLARIFYING / PARTIAL`。

## 1. 一句话结论

ForgeOps 已把 Project DomainLock 固定的本地合成语义和知识版本变成可授权查询、
可确定编译、可结构化校验和可追溯影响的真实产品薄切片，但这不是行业本体、
Agent、大模型、RAG、Workflow 或企业发布能力。

## 2. 为什么做

02.6B 只能回答“项目固定了哪些领域包”，不能回答“一个术语是什么、可用哪个知识
版本、某个结构化结果是否引用了锁内对象”。如果不先把这一层做成确定、可拒绝、
可追溯的纯平台能力，以后的工作流和 Agent 会在歧义和过期知识上静默猜测。

## 3. 开发前后对比

| 问题 | 02.6B 后 | 02.6C 本地薄切片后 |
| --- | --- | --- |
| 语义资产 | Registry 有 Component，但不能查语义 | 严格本体/术语/映射绑定精确 Component 版本 |
| 歧义 | 无运行时结果 | 唯一/歧义/未知分开，静默猜测数为 0 |
| 知识 | 无版本真值 | 保存来源、许可、分类、用途、有效期、摘要和撤回历史 |
| 上下文 | 无 | 按 DomainLock、权限、用途和预算产生不可变 ContextManifest |
| 校验 | 无 | 只校验结构化引用，给出 VALID/INVALID/NEEDS_CLARIFICATION |
| 变更 | 只有包撤回影响 | 可比较语义/知识 v1-v2 并定位 Installation/ProjectDomainLock |

## 4. 用户能在哪些页面做什么

顶层 **Semantic & Knowledge** 页从真实 API/SQLite 读取 Registry 组件，可登记、发布、
撤回语义 payload，浏览 namespace/concept/term/relation/constraint/mapping，创建知识资产和
不可变版本，并查看影响。Project Center 的 **Context** 面板显示当前 DomainLock 与语义清单，
可解析术语/源映射、设定用途/时间/预算编译 ContextManifest，并对 JSON 候选做 Grounding 校验。

## 5. 五分钟成功与拒绝验证

```bash
make epic-02-6c-owner-demo
```

成功路径会创建中性合成领域，证明唯一术语解析、相同输入同一 digest、合法
Grounding、v1/v2 影响和重启后历史可读。拒绝路径会证明歧义/未知不猜、过期/未发布/
用途不匹配知识被排除、超预算确定截断、错误引用被拒绝、Viewer 不能发布且 Outsider 只得 404。

## 6. 页面和 API 截图/证据路径

- 真实页面：`apps/web/src/SemanticKnowledge.tsx` 与 `apps/web/src/ProjectContext.tsx`；
- 真实浏览器/API 证据：`apps/web/e2e/semantic-knowledge.spec.ts`；
- API 合约：`contracts/openapi/forgeops.openapi.json`与 `src/forgeops/semantic_knowledge_api.py`；
- 人读结果：[EPIC-02.6C Evidence](EPIC-02.6C-evidence.md)；
- 机读摘要：`generated-epic-02.6c-evidence.json`（完成提交绑定后生成）。

Playwright 通过页面驱动真实 API 和数据库，不用静态截图代替可操作证据。

## 7. 不可见地基

迁移 `0008`、SQLAlchemy 七类持久化记录、严格 Pydantic/OpenAPI Schema、内容寻址存储、准入
与版本乐观并发、幂等键、跨组织 404 隐藏、审计关联、确定性 canonical JSON/digest，
以及禁止制造领域、LLM、向量/图运行时依赖的架构门。

## 8. 明确未实现

没有 Agent/LLM/RAG/embedding/向量库/图数据库/全文检索/自动推理；没有 Workflow 定义、画布、
Run、Temporal 和调试器；没有行业本体正确性、真实业务、真实 APS/MES/ERP/PLC/DCS 接入、
外部写入、市场/支付、企业签名和许可审核。

## 9. 风险与限制

证据只基于 SQLite、本地合成身份和小型中性资产。未证 PostgreSQL 服务并发/备份恢复、企业
OIDC/SCIM、审计原子性、许可/分类/来源的人员审批、恶意文件扫描、真实数据隐私、跨行业泛化
或自然语言事实正确性。G2/G4/G5A/G5B/PREPROD/PROD/UAT 均不提高。

## 10. 测试数量、覆盖率、源码/证据提交

最终门禁通过 410 个 Python 测试（其中 41 个显式 contract）、6 个 Vitest、3 个真实
Playwright E2E；组合行/分支覆盖率 87.18%。02.6C 专项 290、02.6A 回归 40、02.6B 回归 64
均通过。源码提交、机器证据提交与 SHA-256 见 [EPIC-02.6C Evidence](EPIC-02.6C-evidence.md)
的 Evidence binding；这些数字不包含企业、真实数据或业务验收。

## 11. 是否具备进入 EPIC-02.7 产品设计基线的条件

本地门禁已成立，具备“提请评审 EPIC-02.7”的有限工程前置；不会自动开始。
下一步建议是先进入 EPIC-02.7 冻结产品 UI/UX、高保真工作流工作室原型和设计系统，再由
EPIC-03 实现真实画布与可执行 Run。

## 12. 工作流画布何时可见

EPIC-02.7 才提供接近最终结构、但必须明确标注为“原型”的高保真画布；EPIC-03 才提供真实
连线执行、Run 和调试器。本任务没有进入这两个阶段。
