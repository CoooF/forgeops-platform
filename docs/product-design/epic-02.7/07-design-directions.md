# EPIC-02.7 第三轮视觉方向候选与选择门

状态：`WAITING_FOR_DIRECTION_SELECTION`  
预览入口：`/design-preview/directions`  
共同边界：视觉方向预览、交互原型、本地合成、未接 Workflow/Run/Agent 后端、未运行、建议未执行。

旧候选因产品负责人反馈“总体风格没有变化、框架过于简单、视觉质量太差”全部作废。本轮保留产品信息架构、真实 API 页面和安全边界，视觉层从零重建。

## 设计方法

本轮同时使用 `ui-ux-pro-max` 与 `frontend-design`：

- `ui-ux-pro-max` 用于产品类型、视觉系统、配色、字体、UX、React 和可访问性检索；落实 44px 交互目标、可见焦点、语义 HTML、Escape 关闭弹层、固定元素避让、375px 无横向滚动与 reduced-motion；
- `frontend-design` 用于形成三种明确、可记忆而非换主题色的产品表达；拒绝自动推荐中的 AI 紫色、Inter、装饰光球和营销 Hero；
- 三套仍使用相同 8 模块产品 IA、相同 8 节点 fixture 和相同任务内容，视觉差异不依赖内容作弊。

## 共用合规结构

每套都包含全局 Shell 与项目上下文、8 个一级产品模块、左侧节点/能力库、近白全幅画布、8 个带 DATA/CONTROL typed ports 的代表节点、右侧节点检查器、底部运行/调试台、主 Agent 入口和明确未实现边界。

产品模块固定为：项目、工作流、运行与推演、数据与数据库、主 Agent 中心、Agent 与能力、领域、治理。入口标记 `真实 API`、`混合边界` 或 `原型`；数据库和主 Agent 等未实现模块只打开能力清单，不调用 API，不显示伪成功状态。

## A：静默控制台

**母题**：暖白工程工具、纸面秩序、安静的长期工作环境。

- 结构：左侧产品空间，工作区内再分节点库、近白点阵画布、底部调试台，右侧为稳定节点检查器；
- 视觉：深墨绿、暖白和极少安全橙；Newsreader 与 Manrope 形成工程文档感；圆角只用于容器层级，不嵌套卡片堆；
- 优点：最克制、最耐看，普通工程师的学习成本最低；完整产品 IA 与画布主次最清楚；
- 代价：品牌张力最弱，需要依靠节点语言、端口和主 Agent 协作建立差异；
- 适合：全产品基础 Shell 与默认搭建模式。

## B：Agent 协同中枢

**母题**：深色协作外壳包围一张明亮规划面，目标、主 Agent 和 Evidence 共同组织工作。

- 结构：一级模块进入顶栏；左侧把当前任务、能力库和主 Agent 目标放在一起；中央近白轨道画布围绕协调 Agent；右侧是节点检查器/Evidence Ledger；底部保持 typed-port 调试台；
- 视觉：深青黑外壳、近白画布、青色协作信号与琥珀风险；不是黑色大屏，画布始终是第一视觉；
- 优点：最能表达“AI-native 但不自动执行”，主 Agent 与执行 Agent 区分最直观；辨识度最高；
- 代价：深浅切换对长时工作更有刺激，轨道布局不适合所有复杂拓扑；
- 适合：目标拆解、Agent 协作和运行调查模式。

## C：领域蓝图

**母题**：瑞士现代主义系统地图，黑白网格与单一信号红表达受控关系。

- 结构：左侧产品 System Map；画布左侧结合工作流标题与紧凑能力库；中央四列 INPUT/CONTEXT/REASON/REVIEW 蓝图；右侧独立节点检查器；底部是贯穿全宽的调试/CONTROL 台；
- 视觉：零装饰渐变、无柔和阴影、严格网格、硬边节点和单一信号色；标题控制在工具层级，不做营销 Hero；
- 优点：领域、数据、Agent 与人工评审的关系最清楚，ForgeOps 视觉记忆点最强；
- 代价：表达更强硬，密集编辑时需要更成熟的缩放和响应式策略；
- 适合：领域建模、系统审查和受控关系调查。

## 初步推荐

推荐 **A 作为基础产品 Shell，吸收 B 的主 Agent 目标协作模式和 C 的领域蓝图作为专业视图**。如果只允许选择一个完整方向，A 的长期使用风险最低；如果允许组合，A+B+C 各自承担基础搭建、Agent 协作和领域调查，比强迫一种视觉覆盖全部任务更合理。

这只是设计建议，不构成产品负责人选择。未得到明确选择前，不继续阶段 B，不写 `ACCEPTED_FOR_EPIC_03_IMPLEMENTATION`。

## 截图基线

- `screenshots/direction-a-precision-1440x900.png` · SHA-256 `5b0ecc4cef514702805607698363795e680e9407023cdae8474da4f3d934eadd`
- `screenshots/direction-b-semantic-1440x900.png` · SHA-256 `42fab1ce8c186ee59aff863d5510bbe7436f4a0c1798016c9bcd3062b496b326`
- `screenshots/direction-c-investigation-1440x900.png` · SHA-256 `8c2ac1664cd84cf435d6dd64de8e28fe853e6c1ddbafb7583a4936a720792625`
- `screenshots/module-data-and-databases-1440x900.png` · SHA-256 `7fa6df93061f29c815ea26440a723de990990a3fa720bb866b47dc6bd74ad059`
- `screenshots/module-main-agent-center-1440x900.png` · SHA-256 `19ae9e3de9d6cf20ac322ed3f2e72d05a3c5ba60c6d74251a3497027f97dbf76`

截图由 `apps/web/e2e/design-directions.spec.ts` 在 1440×900 Chrome 视口生成。测试覆盖 8 个产品模块、数据库与主 Agent 模块边界、能力库、typed ports、节点检查器、调试台、主 Agent 开合、无页面/画布溢出、375×812 重排、reduced-motion、浏览器异常和原型意外 API 请求。
