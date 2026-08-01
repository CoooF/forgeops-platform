# EPIC-02.7 当前 UI 与前端现状审计

状态：`PHASE_A_COMPLETE / DIRECTION_A_SELECTED`
审计基线：`7a8e28d`；开始时工作树 clean  
边界：只审计与新增隔离方向预览，不重写或降级真实 API 页面。

## 1. 一句话结论

当前 Web 已有可信、可操作的项目与治理薄切片，但产品形态仍是“后端对象验收台”：真实能力、权限拒绝和数据边界值得保留，导航、任务路径、画布主工作台和前端模块结构必须在 EPIC-03 前重建。

## 2. 真实页面、角色、入口与数据来源

| 入口 | 用户任务 | 状态来源 | 权限与边界 | 处理建议 |
| --- | --- | --- | --- | --- |
| 项目中心 `/` | 切换组织/工作空间/项目，创建与归档项目 | 真实 `/v1/organizations`、Workspace、Project API/DB | 本地合成主体；成员关系由后端授权 | 保留真实闭环；以后作为项目任务入口，弱化“全产品首页”职责 |
| 项目概览 | 查看与修改项目基本事实 | 真实 Project API/DB | `project.update/activate/archive` | 保留，改造为项目概览二级页 |
| 成员权限 | 查看/新增/暂停/撤销成员 | 真实 Membership API/DB | 后端 Scope、默认拒绝、历史保留 | 保留，归入治理/项目设置 |
| 场景包 | 查看与绑定 Scenario Installation | 真实 API/DB | 绑定不等于授权、发布或运行 | 保留，未来合并到“Agent 与能力 / 已安装”任务流 |
| 领域锁 | 查看 current/history、比较和切换 DomainLock | 真实 API/DB | 只读与管理权限分离；不可变历史 | 保留，是 Studio 顶部上下文与领域中心的真值来源 |
| 上下文 | 查询语义、编译 ContextManifest、结构 Grounding | 真实 API/DB | 无 Agent/LLM/RAG；歧义不猜 | 保留，未来转为“数据与知识 / Context 调查”二级页 |
| 审计记录 | 读取项目审计 | 真实 API/DB | `audit.read`，跨 Scope 隐藏 | 保留，归入治理与运行调查 |
| 领域资产 | Registry、组织 Installation、影响与治理 | 真实 API/DB | 幂等、If-Match、撤回/隔离、不物理删除 | 保留，重构为领域中心的支撑页面 |
| 语义与知识 | 语义 payload、知识版本、影响 | 真实 API/DB | LOCAL_SYNTHETIC / NOT_ENTERPRISE_VERIFIED | 保留，重构为数据与知识区的支撑页面 |

当前受控角色为本地 Owner、Editor、Viewer、Outsider、Disabled。`X-ForgeOps-Actor` 只选择受控测试主体，真实权限仍由持久化 Membership 与后端策略决定。PREPROD/PROD 写边界、企业身份、真实数据、Workflow/Run/Agent 均未实现。

## 3. 当前任务路径

当前主路径是“先选身份和层级，再直接操作后端对象”：

```text
本地身份 → 组织 → 工作空间 → 项目
  → 项目概览 / 成员 / 场景包 / DomainLock / Context / 审计
  → 顶层切换 Registry 或 Semantic & Knowledge
```

优点是权限与真实状态可验证；问题是普通工程师的目标、待办、风险、工作流、运行和结果不在主路径中。大量页面以列表、状态徽标、详情、表单重复映射后端对象，不能形成“搭建 → 校验 → 调查 → 决策”的连续产品体验。

## 4. 页面迁移判断

- **保留**：真实 Project、Membership、ProjectPackageBinding、DomainLock、Registry、Semantic/Knowledge、Context、Audit API 与测试选择器。
- **受控改造**：公共 Shell、项目概览、页面标题与状态来源标识；只在不破坏真实闭环和权限拒绝证据时推进。
- **合并/转二级**：成员和审计进入治理；场景包绑定进入能力安装；Context 与语义/知识进入数据与知识；Registry/Installation/DomainLock 组成领域中心。
- **未来淘汰**：把当前顶层三块页面当最终产品一级主工作台的做法；不是删除真实功能，而是改变入口层级。
- **新增原型**：工作流工作室、主 Agent、运行调查、结果比较、数据中心和能力目录必须显著标记为原型/未来能力，不能调用不存在的 API。

## 5. 前端工程审计

### 5.1 体量与耦合

- `App.tsx` 1543 行：Shell、会话加载、Scope 选择、页面切换、权限展示、CRUD 表单与通用组件集中；
- `project-api.ts` 953 行：手写 DTO 和所有 API 方法集中，以泛型强制转换响应，尚无 OpenAPI 生成或运行时响应校验；
- `styles.css` 2552 行：全局选择器、两套 `:root` 与后加的 2026 visual refresh 同时存在，媒体查询和页面样式重复覆盖；
- 页面靠 `surface`/`tab` 本地状态切换，无正式路由、深链、浏览器历史或页面级代码分割；
- React/Vite 与 FastAPI 已物理分进程，但前端内部尚未形成 Shell、Studio、Inspector、Debugger、Builder、Results、Governance 模块边界。

### 5.2 数据与状态

- `project-api.ts` 已集中大部分 `fetch`，比页面散落调用更安全；`status.ts` 仍有另一条直接 fetch 路径；
- Server State、表单状态、选择状态和消息状态均由页面 `useState/useEffect` 手工维护；没有缓存、取消、失效、请求竞态或局部刷新统一策略；
- 客户端用 Membership 推断一部分按钮可见性，真实后端仍会拒绝；未来应由服务器返回的显式 capability/permission 决定产品状态，客户端隐藏不能成为授权证据；
- fixture 尚未集中分层。本阶段新增原型 fixture 位于 `src/design-preview/direction-fixture.ts`，不进入 API Client。

### 5.3 可访问性与响应式

- 已有中文 `aria-label`、真实 label、可见 `:focus-visible`、状态/错误文本，基础方向正确；
- Tabs 未完整实现 `tab/aria-selected/tabpanel` 语义；popover 没有 Dialog 语义、焦点圈定、Esc/返回焦点；动态 notice 统一用 `role=status`，错误与状态等级仍需细化；
- 980/760 像素媒体查询覆盖真实页面，但没有 476×770 核心任务的正式验收基线；
- 当前测试为 6 个 Vitest（主要是 SSR 文本/契约）与 3 个真实 Playwright E2E；没有视觉回归、键盘旅程或自动可访问性测试。

### 5.4 依赖与画布

当前正式依赖只有 React/ReactDOM，尚无 Router、Server State、图标库或画布库。阶段 A 不为了预览引入依赖；画布库、Lucide 与 Router 只在方向选定后，按许可证、维护状态、React 19 兼容性和锁文件审查再决定。

## 6. 来源状态必须统一表达

| 来源 | 页面行为 | 视觉与文案 |
| --- | --- | --- |
| 真实 API | 可读取/写入已实现后端，错误不吞掉 | “真实 API / 本地合成身份和数据” |
| 受控合成演示 | 数据是合成，但 API/DB/权限真实 | “LOCAL_SYNTHETIC / NOT_ENTERPRISE_VERIFIED” |
| 高保真原型 | 只用隔离 fixture 或内存 | “交互原型 / 本地合成 / 未接后端 / 未运行” |
| 未来能力 | 不提供假成功动作 | 禁用或说明“EPIC-03+ 才接入” |

## 7. EPIC-03 前必须解决

1. 建立正式路由和权限感知的全局 Shell，保留真实页面稳定入口；
2. 新增代码按 `app-shell / studio / inspector / debugger / builder / results / governance / fixtures / api` 分层；
3. OpenAPI 生成 TypeScript Client 或至少做自动一致性校验，消除手工 DTO 漂移；
4. API Client、Server State、产品本地状态、原型 fixture 与纯视觉组件分层；
5. 选定画布库并验证许可证、React 19、typed ports、自定义节点、键盘、视口与测试能力；
6. Design Tokens 与基础控件替代全局 CSS 覆盖，新增代码不得继续进入 `styles.css`；
7. 完成弹层焦点管理、Tab 语义、键盘路径、中文最长文案与三视口验收；
8. 建立“真实 API / 原型 / 本地合成 / 未来能力”统一 SourceBadge；
9. Run/权限/节点状态必须只读取后端真值，禁止计时器或动画伪造执行。

## 8. 可以后置

- 多人实时共同编辑、CRDT、共享光标；
- 200—500 节点虚拟化和高级自动布局；
- 公共市场、任意第三方可执行 UI、移动端；
- 场景专用高复杂度图（甘特、故障假设图）与生产数据性能承诺；
- 全站一次性重写现有治理页。

## 9. 基线验证

开始阶段 A 前已通过：`make verify`（410 Python、41 contract、6 Vitest、87.18%）、`make epic-02-6c`（290）、`make epic-02-6c-owner-demo` 与 `make e2e`（3 个真实浏览器路径）。
