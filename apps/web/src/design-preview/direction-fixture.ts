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
    name: "精密工业工作台",
    thesis: "工程图式秩序 · 高密度长时操作",
  },
  {
    id: "semantic",
    code: "B",
    name: "领域建模台",
    thesis: "语义层级可见 · 关系与端口优先",
  },
  {
    id: "investigation",
    code: "C",
    name: "运行推演台",
    thesis: "实际路径突出 · 风险与证据优先",
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
    x: 716,
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
    x: 716,
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
