export type DirectionId = "precision" | "semantic" | "investigation";

export interface StudioNode {
  id: string;
  kind: string;
  title: string;
  subtitle: string;
  x: number;
  y: number;
  inputs: string[];
  outputs: string[];
  control: string[];
  status: "ready" | "warning" | "draft";
  layer: "source" | "context" | "reason" | "result";
}

export const directions: Array<{
  id: DirectionId;
  code: string;
  name: string;
  thesis: string;
}> = [
  {
    id: "precision",
    code: "A",
    name: "静默控制台",
    thesis: "暖白工程工具 · 克制、清晰、适合长时工作",
  },
  {
    id: "semantic",
    code: "B",
    name: "Agent 协同中枢",
    thesis: "深色智能空间 · 任务、对话与证据成为中心",
  },
  {
    id: "investigation",
    code: "C",
    name: "领域蓝图",
    thesis: "瑞士式系统地图 · 高对比、模块化、关系优先",
  },
];

export const nodes: StudioNode[] = [
  {
    id: "trigger",
    kind: "触发器",
    title: "订单变化触发",
    subtitle: "事件输入 · v1",
    x: 34,
    y: 100,
    inputs: [],
    outputs: ["变更事件"],
    control: ["成功", "失败"],
    status: "ready",
    layer: "source",
  },
  {
    id: "quality",
    kind: "数据",
    title: "输入质量门",
    subtitle: "快照与质量报告",
    x: 208,
    y: 70,
    inputs: ["变更事件"],
    outputs: ["合格数据", "缺口报告"],
    control: ["通过", "需补充", "失败"],
    status: "ready",
    layer: "source",
  },
  {
    id: "semantic",
    kind: "语义",
    title: "术语与映射解析",
    subtitle: "DomainLock 精确引用",
    x: 208,
    y: 250,
    inputs: ["合格数据"],
    outputs: ["规范对象", "歧义清单"],
    control: ["已解析", "需澄清"],
    status: "warning",
    layer: "context",
  },
  {
    id: "knowledge",
    kind: "知识",
    title: "装配受控上下文",
    subtitle: "ContextManifest",
    x: 390,
    y: 250,
    inputs: ["规范对象"],
    outputs: ["上下文引用", "排除项"],
    control: ["完成", "证据不足"],
    status: "ready",
    layer: "context",
  },
  {
    id: "agent",
    kind: "执行 Agent",
    title: "协调建议 Agent",
    subtitle: "模型 / 工具 / 预算待配置",
    x: 390,
    y: 70,
    inputs: ["合格数据", "上下文引用"],
    outputs: ["结构化建议", "依据引用"],
    control: ["成功", "待人工", "失败"],
    status: "draft",
    layer: "reason",
  },
  {
    id: "decision",
    kind: "决策",
    title: "风险分流",
    subtitle: "EXCLUSIVE 控制分支",
    x: 566,
    y: 160,
    inputs: ["结构化建议"],
    outputs: ["候选集合"],
    control: ["可评审", "需重算", "无可行结果"],
    status: "ready",
    layer: "reason",
  },
  {
    id: "human",
    kind: "人工",
    title: "负责人评审",
    subtitle: "批注 / 驳回 / 要求重算",
    x: 682,
    y: 70,
    inputs: ["候选集合", "依据引用"],
    outputs: ["评审决定"],
    control: ["通过", "驳回", "重算"],
    status: "draft",
    layer: "result",
  },
  {
    id: "collector",
    kind: "结果汇聚",
    title: "建议结果收集器",
    subtitle: "ADVISORY_NOT_EXECUTED",
    x: 682,
    y: 280,
    inputs: ["候选集合", "评审决定"],
    outputs: ["结果信封", "证据包"],
    control: ["形成建议", "部分结果", "失败"],
    status: "ready",
    layer: "result",
  },
];

export const capabilityGroups = [
  {
    name: "触发与数据",
    items: ["事件触发器", "数据产品", "质量门", "快照引用"],
  },
  {
    name: "语义与知识",
    items: ["术语解析", "语义映射", "知识检索", "上下文装配"],
  },
  { name: "推演与协作", items: ["执行 Agent", "算法", "仿真", "人工评审"] },
  { name: "结果", items: ["决策分支", "结果收集器", "页面输出", "报告导出"] },
];

export type ProductModuleId =
  | "projects"
  | "workflows"
  | "runs"
  | "data"
  | "main-agent"
  | "capabilities"
  | "domains"
  | "governance";

export const productModules: Array<{
  id: ProductModuleId;
  icon: string;
  name: string;
  short: string;
  source: "真实 API" | "混合边界" | "产品原型";
  description: string;
  items: Array<{ name: string; state: "真实 API" | "原型" | "未来能力" }>;
}> = [
  {
    id: "projects",
    icon: "项",
    name: "项目",
    short: "范围与任务",
    source: "真实 API",
    description: "组织、工作空间、项目、成员和任务入口。",
    items: [
      { name: "项目中心", state: "真实 API" },
      { name: "项目概览", state: "真实 API" },
      { name: "成员与权限", state: "真实 API" },
      { name: "项目风险与待办", state: "原型" },
    ],
  },
  {
    id: "workflows",
    icon: "流",
    name: "工作流",
    short: "搭建与校验",
    source: "产品原型",
    description: "画布、版本、校验、发布与调试入口。",
    items: [
      { name: "工作流列表", state: "原型" },
      { name: "工作流工作室", state: "原型" },
      { name: "版本与发布", state: "未来能力" },
      { name: "调试器", state: "未来能力" },
    ],
  },
  {
    id: "runs",
    icon: "运",
    name: "运行与推演",
    short: "路径与结果",
    source: "产品原型",
    description: "Run 调查、候选比较、Evidence、风险与结果。",
    items: [
      { name: "运行总览", state: "原型" },
      { name: "实际路径与 Trace", state: "原型" },
      { name: "候选方案比较", state: "原型" },
      { name: "结果与人工评审", state: "原型" },
    ],
  },
  {
    id: "data",
    icon: "数",
    name: "数据与数据库",
    short: "源 / 库 / Schema",
    source: "混合边界",
    description: "管理数据来源、数据库、结构、质量、快照与知识上下文。",
    items: [
      { name: "数据源与数据库实例", state: "原型" },
      { name: "Schema 与字段目录", state: "原型" },
      { name: "数据产品与质量规则", state: "未来能力" },
      { name: "快照与 Evidence", state: "未来能力" },
      { name: "语义与知识", state: "真实 API" },
      { name: "ContextManifest", state: "真实 API" },
    ],
  },
  {
    id: "main-agent",
    icon: "主",
    name: "主 Agent 中心",
    short: "协作与 Builder",
    source: "产品原型",
    description: "管理贯穿项目的主 Agent，而不是执行节点。",
    items: [
      { name: "主 Agent 配置", state: "原型" },
      { name: "协作会话与目标", state: "原型" },
      { name: "Builder 草稿任务", state: "原型" },
      { name: "模型路由与降级", state: "未来能力" },
      { name: "预算、评测与审计", state: "未来能力" },
    ],
  },
  {
    id: "capabilities",
    icon: "能",
    name: "Agent 与能力",
    short: "装配与目录",
    source: "产品原型",
    description: "执行 Agent 与可安装能力的治理和装配。",
    items: [
      { name: "执行 Agent Profile", state: "原型" },
      { name: "模型与工具绑定", state: "原型" },
      { name: "Skill / MCP", state: "原型" },
      { name: "算法 / 仿真 / 连接器", state: "原型" },
      { name: "企业能力目录", state: "未来能力" },
    ],
  },
  {
    id: "domains",
    icon: "域",
    name: "领域",
    short: "Registry 与锁",
    source: "真实 API",
    description: "领域包、组织安装、DomainLock 与影响分析。",
    items: [
      { name: "领域 Registry", state: "真实 API" },
      { name: "组织 Installation", state: "真实 API" },
      { name: "项目 DomainLock", state: "真实 API" },
      { name: "Overlay 与映射", state: "原型" },
    ],
  },
  {
    id: "governance",
    icon: "治",
    name: "治理",
    short: "权限与审计",
    source: "混合边界",
    description: "组织、权限、环境、策略和审计边界。",
    items: [
      { name: "成员与 Scope", state: "真实 API" },
      { name: "项目审计", state: "真实 API" },
      { name: "环境与运行策略", state: "原型" },
      { name: "企业身份与策略发布", state: "未来能力" },
    ],
  },
];
