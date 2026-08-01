export type PrototypeView =
  "project" | "studio" | "runs" | "data" | "agents" | "domains" | "governance";

export interface AgentToolAssembly {
  model: string;
  skills: Array<{ name: string; version: string }>;
  mcps: Array<{ name: string; version: string }>;
  permissions: string[];
  budget: string;
}

export interface PrototypeNode {
  id: string;
  type: "trigger" | "data" | "semantic" | "agent" | "human" | "output";
  kind: string;
  title: string;
  description: string;
  state: "ready" | "warning" | "draft";
  inputs: string[];
  outputs: string[];
  controls: string[];
  assembly?: AgentToolAssembly;
}

export const prototypeNavigation: Array<{
  id: PrototypeView;
  label: string;
  short: string;
  source: "真实 API" | "混合边界" | "本地原型";
}> = [
  { id: "project", label: "项目", short: "目标与任务", source: "真实 API" },
  { id: "studio", label: "工作流", short: "搭建与校验", source: "本地原型" },
  { id: "runs", label: "运行与推演", short: "路径与结果", source: "本地原型" },
  {
    id: "data",
    label: "数据与知识",
    short: "源、库与证据",
    source: "混合边界",
  },
  {
    id: "agents",
    label: "Agent 与能力",
    short: "节点级装配",
    source: "本地原型",
  },
  { id: "domains", label: "领域", short: "Registry 与锁", source: "真实 API" },
  { id: "governance", label: "治理", short: "权限与审计", source: "混合边界" },
];

export const prototypeNodes: [PrototypeNode, ...PrototypeNode[]] = [
  {
    id: "event",
    type: "trigger",
    kind: "触发器",
    title: "订单变化触发",
    description: "接收受控事件引用，不接生产事件流",
    state: "ready",
    inputs: [],
    outputs: ["变更事件"],
    controls: ["成功", "失败"],
  },
  {
    id: "quality",
    type: "data",
    kind: "数据质量门",
    title: "校验输入快照",
    description: "验证必填字段、时效和数据责任人",
    state: "warning",
    inputs: ["变更事件"],
    outputs: ["合格快照", "缺口报告"],
    controls: ["通过", "待补充", "失败"],
  },
  {
    id: "context-agent",
    type: "agent",
    kind: "执行 Agent",
    title: "上下文装配 Agent",
    description: "检索受控语义、知识和数据产品引用",
    state: "ready",
    inputs: ["合格快照"],
    outputs: ["ContextManifest", "排除项"],
    controls: ["完成", "证据不足", "失败"],
    assembly: {
      model: "轻量检索模型 / v1",
      skills: [
        { name: "语义映射解析", version: "1.4.2" },
        { name: "上下文裁剪", version: "0.9.8" },
      ],
      mcps: [
        { name: "语义知识 MCP", version: "2.1" },
        { name: "数据目录 MCP", version: "1.8" },
      ],
      permissions: ["semantic.read", "knowledge.read", "catalog.read"],
      budget: "18k tokens / 单次",
    },
  },
  {
    id: "planner-agent",
    type: "agent",
    kind: "执行 Agent",
    title: "候选方案 Agent",
    description: "生成结构化候选，不执行任何外部动作",
    state: "draft",
    inputs: ["合格快照", "ContextManifest"],
    outputs: ["候选集合", "依据引用"],
    controls: ["完成", "待人工", "失败"],
    assembly: {
      model: "受控推理模型 / 待授权",
      skills: [
        { name: "约束建模", version: "2.0.1" },
        { name: "候选生成", version: "1.7.0" },
      ],
      mcps: [{ name: "规则目录 MCP", version: "3.0" }],
      permissions: ["snapshot.read", "rules.read", "proposal.create.local"],
      budget: "42k tokens / 单次",
    },
  },
  {
    id: "risk-agent",
    type: "agent",
    kind: "执行 Agent",
    title: "风险评估 Agent",
    description: "独立复核候选并形成风险与证据缺口",
    state: "ready",
    inputs: ["候选集合", "依据引用"],
    outputs: ["风险清单", "可评审候选"],
    controls: ["可评审", "需重算", "失败"],
    assembly: {
      model: "规则优先模型 / v2",
      skills: [{ name: "风险分级", version: "1.5.3" }],
      mcps: [
        { name: "证据索引 MCP", version: "1.2" },
        { name: "规则目录 MCP", version: "3.0" },
      ],
      permissions: ["evidence.read", "rules.read", "risk.write.local"],
      budget: "16k tokens / 单次",
    },
  },
  {
    id: "review",
    type: "human",
    kind: "人工评审",
    title: "项目负责人评审",
    description: "批注、驳回或要求重算；不代表已审批",
    state: "draft",
    inputs: ["可评审候选", "风险清单"],
    outputs: ["评审意见"],
    controls: ["建议通过", "驳回", "重算"],
  },
  {
    id: "result",
    type: "output",
    kind: "结果收集器",
    title: "建议结果信封",
    description: "页面、报告与 API 提案入口，均未执行",
    state: "ready",
    inputs: ["评审意见", "可评审候选"],
    outputs: ["结果页面", "证据包"],
    controls: ["形成建议", "部分结果", "失败"],
  },
];

export const capabilityCatalog = [
  { kind: "Skill", name: "约束建模", version: "2.0.1", trust: "已审核" },
  { kind: "Skill", name: "候选生成", version: "1.7.0", trust: "已审核" },
  { kind: "Skill", name: "风险分级", version: "1.5.3", trust: "已审核" },
  { kind: "MCP", name: "数据目录 MCP", version: "1.8", trust: "只读" },
  { kind: "MCP", name: "规则目录 MCP", version: "3.0", trust: "只读" },
  { kind: "MCP", name: "证据索引 MCP", version: "1.2", trust: "只读" },
];

export const syntheticRun = {
  id: "RUN-SYN-0247",
  status: "等待人工 / 本地合成",
  path: [
    "校验输入快照",
    "上下文装配 Agent",
    "候选方案 Agent",
    "风险评估 Agent",
    "项目负责人评审",
  ],
  candidates: [
    {
      id: "A",
      title: "稳态优先",
      score: "82",
      risk: "低",
      evidence: "11 / 12",
    },
    { id: "B", title: "交付优先", score: "76", risk: "中", evidence: "9 / 12" },
    {
      id: "C",
      title: "资源均衡",
      score: "71",
      risk: "中",
      evidence: "10 / 12",
    },
  ],
};
