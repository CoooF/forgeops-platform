import { useEffect, useRef, useState } from "react";

import {
  directions,
  nodes,
  productModules,
  type DirectionId,
  type ProductModuleId,
  type StudioNode,
} from "./direction-fixture";
import "./design-directions.css";

const directionIds = new Set<DirectionId>([
  "precision",
  "semantic",
  "investigation",
]);

const fallbackNode: StudioNode = {
  id: "agent",
  kind: "执行 Agent",
  title: "协调建议 Agent",
  subtitle: "独立装配 · 2 Skill · 1 MCP",
  x: 0,
  y: 0,
  inputs: ["受控上下文"],
  outputs: ["结构化建议"],
  control: ["成功", "待人工", "失败"],
  status: "draft",
  layer: "reason",
  assembly: {
    model: "受控推理模型 / 待授权",
    skills: ["需求约束解析", "候选方案生成"],
    mcps: ["数据目录 MCP"],
    permissionScope: "只读数据产品 · 禁止外部写入",
  },
};

const fallbackDirection = {
  id: "precision" as const,
  code: "A",
  name: "静默控制台",
  thesis: "暖白工程工具 · 克制、清晰、适合长时工作",
};

function initialDirection(): DirectionId {
  const value = new URLSearchParams(window.location.search).get("direction");
  return directionIds.has(value as DirectionId)
    ? (value as DirectionId)
    : "precision";
}

export function DesignDirections() {
  const [direction, setDirection] = useState<DirectionId>(initialDirection);
  const [productModuleId, setProductModuleId] =
    useState<ProductModuleId>("workflows");
  const [selectedNodeId, setSelectedNodeId] = useState("agent");
  const [modulePreviewOpen, setModulePreviewOpen] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const moduleCloseRef = useRef<HTMLButtonElement>(null);
  const moduleTriggerRef = useRef<HTMLButtonElement | null>(null);

  const selectedModule =
    productModules.find((item) => item.id === productModuleId) ??
    productModules[1];
  const selectedNode =
    nodes.find((item) => item.id === selectedNodeId) ?? fallbackNode;
  const currentDirection =
    directions.find((item) => item.id === direction) ?? fallbackDirection;

  useEffect(() => {
    if (!modulePreviewOpen) return;
    moduleCloseRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModulePreviewOpen(false);
        moduleTriggerRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [modulePreviewOpen]);

  function chooseDirection(next: DirectionId) {
    setDirection(next);
    setModulePreviewOpen(false);
    setAgentOpen(false);
    const url = new URL(window.location.href);
    url.searchParams.set("direction", next);
    window.history.replaceState({}, "", url);
  }

  function chooseModule(id: ProductModuleId, trigger: HTMLButtonElement) {
    setProductModuleId(id);
    moduleTriggerRef.current = trigger;
    setModulePreviewOpen(id !== "workflows");
  }

  function closeModulePreview() {
    setModulePreviewOpen(false);
    moduleTriggerRef.current?.focus();
  }

  const workspaceProps: WorkspaceProps = {
    selectedNode,
    selectedNodeId,
    onSelectNode: setSelectedNodeId,
    productModuleId,
    onChooseModule: chooseModule,
    onToggleAgent: () => {
      setAgentOpen((open) => !open);
    },
  };

  return (
    <main className={`preview-root direction-${direction}`}>
      <a className="skip-link" href="#design-main">
        跳到方向主体
      </a>
      <header className="preview-gate" data-testid="prototype-boundary">
        <div className="gate-title">
          <strong>EPIC—02.7</strong>
          <span>方向 A 已选定 · 正在进入高保真原型阶段</span>
        </div>
        <div className="gate-boundaries">
          <span>本地合成</span>
          <span>交互原型</span>
          <span>未接 Workflow / Run / Agent 后端</span>
          <b>未运行 · 建议未执行</b>
        </div>
        <a href="/">返回真实 API 页面</a>
      </header>

      <nav className="direction-switcher" aria-label="视觉方向">
        {directions.map((item) => (
          <button
            key={item.id}
            className={direction === item.id ? "active" : ""}
            aria-pressed={direction === item.id}
            onClick={() => {
              chooseDirection(item.id);
            }}
          >
            <span>{item.code}</span>
            <div>
              <strong>{item.name}</strong>
              <small>{item.thesis}</small>
            </div>
          </button>
        ))}
      </nav>

      <section
        className="direction-stage"
        data-testid={`direction-${direction}`}
        aria-label={`${currentDirection.name}视觉方向`}
      >
        {direction === "precision" && <QuietControl {...workspaceProps} />}
        {direction === "semantic" && <AgenticOrbit {...workspaceProps} />}
        {direction === "investigation" && (
          <LivingBlueprint {...workspaceProps} />
        )}
      </section>

      {modulePreviewOpen && selectedModule && (
        <div className="module-scrim" onMouseDown={closeModulePreview}>
          <aside
            className="module-preview-drawer"
            role="dialog"
            aria-modal="true"
            aria-label={`${selectedModule.name}模块预览`}
            onMouseDown={(event) => {
              event.stopPropagation();
            }}
          >
            <header>
              <SourceBadge source={selectedModule.source} />
              <button
                ref={moduleCloseRef}
                aria-label="关闭模块预览"
                onClick={closeModulePreview}
              >
                <CloseIcon />
              </button>
            </header>
            <div className="module-intro">
              <span>产品模块 / {selectedModule.icon}</span>
              <h2>{selectedModule.name}</h2>
              <p>{selectedModule.description}</p>
            </div>
            <div className="module-preview-items">
              {selectedModule.items.map((item, index) => (
                <div key={item.name}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <strong>{item.name}</strong>
                  <em className={`item-${item.state.replaceAll(" ", "-")}`}>
                    {item.state}
                  </em>
                </div>
              ))}
            </div>
            <footer>
              <BoundaryIcon />
              <p>
                <strong>产品框架预览</strong>
                未接对应后端，不产生数据库、Agent 或运行状态。
              </p>
            </footer>
          </aside>
        </div>
      )}

      <button
        className="main-agent-entry"
        aria-expanded={agentOpen}
        onClick={() => {
          setAgentOpen((open) => !open);
        }}
      >
        <AgentSparkIcon />
        <span>主 Agent</span>
        <small>协作入口</small>
      </button>
      {agentOpen && (
        <aside
          className="agent-dialog"
          role="dialog"
          aria-label="主 Agent 协作预览"
        >
          <header>
            <AgentSparkIcon />
            <div>
              <strong>主 Agent</strong>
              <span>项目级协调层 · 不参与具体执行</span>
            </div>
            <button
              aria-label="关闭主 Agent 预览"
              onClick={() => {
                setAgentOpen(false);
              }}
            >
              <CloseIcon />
            </button>
          </header>
          <div>
            <span>LOCAL PROTOTYPE</span>
            <h2>从目标开始，而不是从空白画布开始。</h2>
            <p>
              可以讨论范围、生成 Builder 草稿、拆解任务和解释证据边界；它没有
              DATA/CONTROL 端口，不安装执行节点的 Skill/MCP，也不会运行工作流。
            </p>
          </div>
          <footer>无执行端口 · 未调用模型 · 无上下文发送 · 无后端状态</footer>
        </aside>
      )}
    </main>
  );
}

interface WorkspaceProps {
  selectedNode: StudioNode;
  selectedNodeId: string;
  onSelectNode: (id: string) => void;
  productModuleId: ProductModuleId;
  onChooseModule: (id: ProductModuleId, trigger: HTMLButtonElement) => void;
  onToggleAgent: () => void;
}

function QuietControl(props: WorkspaceProps) {
  return (
    <div className="quiet-shell">
      <header className="quiet-topbar">
        <BrandMark variant="quiet" />
        <div className="quiet-context">
          <span>合成协同实验室</span>
          <strong>订单与资源协调</strong>
          <small>协调基础域 @ 0.2</small>
        </div>
        <div className="quiet-actions">
          <button>原型校验</button>
          <button disabled>运行工作流</button>
        </div>
      </header>
      <ProductNavigation variant="quiet" {...props} />
      <main className="quiet-workspace" id="design-main">
        <header className="workspace-heading">
          <div>
            <span>WORKFLOW / DRAFT 07</span>
            <h1>订单协调工作流</h1>
            <p>用受控上下文生成可评审建议，不直接操作工业系统。</p>
          </div>
          <div className="workspace-state">
            <span>草稿</span>
            <strong>8 个节点</strong>
          </div>
        </header>
        <div className="workspace-tabs" role="tablist" aria-label="工作室视图">
          <button role="tab" aria-selected="true">
            结构
          </button>
          <button role="tab" aria-selected="false">
            输入与变量
          </button>
          <button role="tab" aria-selected="false">
            Evidence
          </button>
        </div>
        <div className="quiet-studio-body">
          <CapabilityShelf variant="quiet" />
          <section className="canvas-area quiet-canvas" aria-label="工作流画布">
            <div className="quiet-flowline" aria-hidden="true" />
            {nodes.map((node, index) => (
              <NodeCard
                key={node.id}
                node={node}
                index={index}
                selected={props.selectedNodeId === node.id}
                onSelect={props.onSelectNode}
              />
            ))}
            <CanvasBoundary />
          </section>
        </div>
        <DebugConsole variant="quiet" selectedNode={props.selectedNode} />
      </main>
      <aside className="quiet-inspector" aria-label="节点检查器">
        <header>
          <span>节点详情</span>
          <b>···</b>
        </header>
        <div className="inspector-node-type">
          <NodeGlyph kind={props.selectedNode.kind} />
          <div>
            <span>{props.selectedNode.kind}</span>
            <h2>{props.selectedNode.title}</h2>
          </div>
        </div>
        <dl>
          <div>
            <dt>输入</dt>
            <dd>{props.selectedNode.inputs.length || "无"}</dd>
          </div>
          <div>
            <dt>数据输出</dt>
            <dd>{props.selectedNode.outputs.length}</dd>
          </div>
          <div>
            <dt>控制出口</dt>
            <dd>{props.selectedNode.control.length}</dd>
          </div>
          <div>
            <dt>模型</dt>
            <dd>{props.selectedNode.assembly?.model ?? "不适用"}</dd>
          </div>
        </dl>
        {props.selectedNode.assembly ? (
          <section
            className="agent-assembly"
            aria-label="执行 Agent 独立能力装配"
          >
            <header>
              <div>
                <span>节点级装配</span>
                <strong>仅属于此执行 Agent</strong>
              </div>
              <em>本地原型</em>
            </header>
            <div className="assembly-group">
              <span>Skills</span>
              <div>
                {props.selectedNode.assembly.skills.map((skill) => (
                  <b key={skill}>{skill}</b>
                ))}
                <button title="原型操作，不会实际安装 Skill">
                  ＋ 安装 Skill
                </button>
              </div>
            </div>
            <div className="assembly-group">
              <span>MCP Servers</span>
              <div>
                {props.selectedNode.assembly.mcps.map((mcp) => (
                  <b key={mcp}>{mcp}</b>
                ))}
                <button title="原型操作，不会连接 MCP Server">
                  ＋ 连接 MCP
                </button>
              </div>
            </div>
            <p>{props.selectedNode.assembly.permissionScope}</p>
          </section>
        ) : (
          <div className="non-agent-boundary">
            此节点不是执行 Agent，不提供 Skill / MCP 装配槽。
          </div>
        )}
        <div className="inspector-warning">
          <BoundaryIcon />
          <span>失败出口尚未连接</span>
        </div>
        <button className="inspector-agent-link" onClick={props.onToggleAgent}>
          交给主 Agent 解释
          <ArrowIcon />
        </button>
      </aside>
    </div>
  );
}

function AgenticOrbit(props: WorkspaceProps) {
  return (
    <div className="orbit-shell">
      <header className="orbit-topbar">
        <BrandMark variant="orbit" />
        <ProductNavigation variant="orbit" {...props} />
        <div className="orbit-status">
          <i />
          LOCAL / SAFE
        </div>
      </header>
      <aside className="orbit-mission">
        <span className="eyebrow">CURRENT MISSION</span>
        <h1>让订单变化成为一条可解释的建议。</h1>
        <p>主 Agent 正在浏览本地原型结构；没有模型调用，也没有运行实例。</p>
        <div className="mission-facts">
          <div>
            <span>领域锁</span>
            <strong>0.2</strong>
          </div>
          <div>
            <span>能力</span>
            <strong>08</strong>
          </div>
          <div>
            <span>风险</span>
            <strong>01</strong>
          </div>
        </div>
        <CapabilityShelf variant="orbit" />
        <button onClick={props.onToggleAgent}>
          <AgentSparkIcon /> 与主 Agent 讨论目标
        </button>
      </aside>
      <main className="orbit-workspace" id="design-main">
        <div className="orbit-heading">
          <div>
            <span>ORCHESTRATION MAP</span>
            <strong>协调建议流程 / 草稿 07</strong>
          </div>
          <button disabled>RUN DISCONNECTED</button>
        </div>
        <section className="canvas-area orbit-map" aria-label="Agent 协同轨道">
          <svg viewBox="0 0 800 520" aria-hidden="true">
            <ellipse cx="400" cy="260" rx="290" ry="168" />
            <ellipse cx="400" cy="260" rx="190" ry="112" />
            <path d="M132 160 C235 58 574 50 670 168" />
            <path d="M134 358 C280 472 552 468 674 352" />
          </svg>
          <div className="orbit-core">
            <AgentSparkIcon />
            <span>协调建议</span>
            <strong>等待配置</strong>
          </div>
          {nodes.map((node, index) => (
            <NodeCard
              key={node.id}
              node={node}
              index={index}
              selected={props.selectedNodeId === node.id}
              onSelect={props.onSelectNode}
            />
          ))}
          <CanvasBoundary />
        </section>
        <DebugConsole variant="orbit" selectedNode={props.selectedNode} />
      </main>
      <aside className="orbit-evidence" aria-label="节点检查器">
        <header>
          <span>节点检查器 / EVIDENCE</span>
          <b>0 / 4</b>
        </header>
        <h2>{props.selectedNode.title}</h2>
        <p>{props.selectedNode.subtitle}</p>
        <ol>
          <li>
            <i />
            输入来源 <strong>本地 fixture</strong>
          </li>
          <li>
            <i />
            DomainLock <strong>可见</strong>
          </li>
          <li>
            <i />
            模型调用 <strong>未发生</strong>
          </li>
          <li className="warning">
            <i />
            失败出口 <strong>未连接</strong>
          </li>
        </ol>
        <div className="orbit-notice">失败出口尚未连接</div>
      </aside>
    </div>
  );
}

function LivingBlueprint(props: WorkspaceProps) {
  return (
    <div className="blueprint-shell">
      <header className="blueprint-head">
        <BrandMark variant="blueprint" />
        <div>
          <span>PRODUCT SYSTEM / 02.7</span>
          <strong>协调基础域</strong>
        </div>
        <p>
          本地合成产品地图
          <br />
          不代表运行能力
        </p>
      </header>
      <ProductNavigation variant="blueprint" {...props} />
      <main className="blueprint-main" id="design-main">
        <header className="blueprint-title">
          <span>WORKFLOW BLUEPRINT · 07</span>
          <h1>系统关系图</h1>
          <p>
            领域、数据、Agent 与人工决策在同一张受控蓝图中，但执行仍然不存在。
          </p>
          <CapabilityShelf variant="blueprint" />
        </header>
        <section className="canvas-area blueprint-flow" aria-label="领域蓝图">
          <div className="blueprint-columns" aria-hidden="true">
            <span>01 / INPUT</span>
            <span>02 / CONTEXT</span>
            <span>03 / REASON</span>
            <span>04 / REVIEW</span>
          </div>
          {nodes.map((node, index) => (
            <NodeCard
              key={node.id}
              node={node}
              index={index}
              selected={props.selectedNodeId === node.id}
              onSelect={props.onSelectNode}
            />
          ))}
          <CanvasBoundary />
        </section>
        <aside className="blueprint-inspector" aria-label="节点检查器">
          <span>NODE INSPECTOR / 01</span>
          <div>
            <NodeGlyph kind={props.selectedNode.kind} />
            <h2>{props.selectedNode.title}</h2>
            <p>{props.selectedNode.subtitle}</p>
          </div>
          <dl>
            <div>
              <dt>DATA 输入</dt>
              <dd>{props.selectedNode.inputs.length}</dd>
            </div>
            <div>
              <dt>DATA 输出</dt>
              <dd>{props.selectedNode.outputs.length}</dd>
            </div>
            <div>
              <dt>CONTROL</dt>
              <dd>{props.selectedNode.control.length}</dd>
            </div>
            <div>
              <dt>执行状态</dt>
              <dd>未运行</dd>
            </div>
          </dl>
        </aside>
        <footer className="blueprint-footer" aria-label="运行与调试控制台">
          <div>
            <span>调试台 / SELECTED</span>
            <strong>{props.selectedNode.title}</strong>
          </div>
          <div>
            <span>端口发射 / CONTROL</span>
            <strong>{props.selectedNode.control.join(" / ")}</strong>
          </div>
          <div className="blueprint-warning">
            <BoundaryIcon />
            失败出口尚未连接
          </div>
        </footer>
      </main>
    </div>
  );
}

function ProductNavigation({
  variant,
  productModuleId,
  onChooseModule,
}: WorkspaceProps & { variant: "quiet" | "orbit" | "blueprint" }) {
  return (
    <nav
      className={`global-product-nav nav-${variant}`}
      aria-label="ForgeOps 产品模块"
    >
      {variant !== "orbit" && (
        <header>
          <span>{variant === "quiet" ? "产品空间" : "SYSTEM MAP"}</span>
          <small>8 MODULES</small>
        </header>
      )}
      {productModules.map((item, index) => (
        <button
          key={item.id}
          className={productModuleId === item.id ? "active" : ""}
          aria-pressed={productModuleId === item.id}
          aria-label={`${item.name}，${item.source}`}
          onClick={(event) => {
            onChooseModule(item.id, event.currentTarget);
          }}
        >
          <ModuleGlyph index={index} />
          <span>{item.name}</span>
          {variant !== "orbit" && <small>{item.short}</small>}
          <em>{item.source === "产品原型" ? "原型" : item.source}</em>
        </button>
      ))}
    </nav>
  );
}

const capabilityItems = [
  { name: "事件触发器", action: "＋ 节点" },
  { name: "数据产品", action: "＋ 节点" },
  { name: "知识检索", action: "＋ 节点" },
  { name: "术语解析", action: "＋ 节点" },
  { name: "数据转换", action: "＋ 节点" },
  { name: "执行 Agent", action: "＋ 节点" },
  { name: "Skill 能力", action: "装配" },
  { name: "MCP Server", action: "装配" },
];

function CapabilityShelf({
  variant,
}: {
  variant: "quiet" | "orbit" | "blueprint";
}) {
  return (
    <aside
      className={`capability-shelf shelf-${variant}`}
      aria-label="节点与能力库"
    >
      <header>
        <span>节点与能力</span>
        <small>8 AVAILABLE</small>
      </header>
      <div>
        {capabilityItems.map((item, index) => (
          <button key={item.name} title={`${item.name}，仅用于视觉预览`}>
            <ModuleGlyph index={index} />
            <span>{item.name}</span>
            <b>{item.action}</b>
          </button>
        ))}
      </div>
    </aside>
  );
}

function DebugConsole({
  variant,
  selectedNode,
}: {
  variant: "quiet" | "orbit";
  selectedNode: StudioNode;
}) {
  return (
    <section
      className={`debug-console console-${variant}`}
      aria-label="运行与调试控制台"
    >
      <div>
        <span>调试台</span>
        <strong>端口发射</strong>
        <span>Evidence</span>
        <span>Trace</span>
      </div>
      <p>
        <b>{selectedNode.title}</b> 尚无真实运行数据
      </p>
      <dl>
        <div>
          <dt>DATA</dt>
          <dd>0 emissions</dd>
        </div>
        <div>
          <dt>CONTROL</dt>
          <dd>NOT EXECUTED</dd>
        </div>
      </dl>
    </section>
  );
}

function NodeCard({
  node,
  index,
  selected,
  onSelect,
}: {
  node: StudioNode;
  index: number;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      className={`studio-node node-${String(index)} ${selected ? "selected" : ""}`}
      aria-pressed={selected}
      onClick={() => {
        onSelect(node.id);
      }}
    >
      <span className="node-kicker">
        <NodeGlyph kind={node.kind} />
        {node.kind}
      </span>
      <strong>{node.title}</strong>
      <small>{node.subtitle}</small>
      {node.assembly && (
        <span className="node-assembly-summary">
          <b>{node.assembly.skills.length} Skill</b>
          <b>{node.assembly.mcps.length} MCP</b>
        </span>
      )}
      <span className="node-status">
        {node.status === "ready"
          ? "已配置"
          : node.status === "warning"
            ? "需澄清"
            : "草稿"}
      </span>
      <span className="node-ports" aria-label="DATA 与 CONTROL typed ports">
        <i className="data-port" />
        <b>DATA</b>
        <i className="control-port" />
        <b>CONTROL</b>
      </span>
    </button>
  );
}

function CanvasBoundary() {
  return (
    <div className="canvas-boundary">
      <BoundaryIcon />
      <span>结构预览</span>
      <strong>NOT EXECUTED</strong>
    </div>
  );
}

function SourceBadge({ source }: { source: string }) {
  return <span className="source-badge">{source}</span>;
}

function BrandMark({ variant }: { variant: string }) {
  return (
    <div className={`brand-mark brand-${variant}`}>
      <svg viewBox="0 0 40 40" aria-hidden="true">
        <path d="M6 6h28v28H6zM13 13h14M13 20h9M13 27h14" />
      </svg>
      <div>
        <strong>ForgeOps</strong>
        <span>INDUSTRIAL INTELLIGENCE</span>
      </div>
    </div>
  );
}

function ModuleGlyph({ index }: { index: number }) {
  const paths = [
    "M4 7h16v13H4zM8 7V4h8v3",
    "M5 6h5v5H5zM14 13h5v5h-5zM10 8h4v1M16 9v4",
    "M4 18V6m0 12h16M7 14l4-4 3 2 5-6",
    "M5 5h14v5H5zM5 14h14v5H5zM8 8h.01M8 17h.01",
    "M12 3l2.2 4.6L19 10l-4.8 2.4L12 17l-2.2-4.6L5 10l4.8-2.4z",
    "M4 8h16M4 16h16M8 4v16M16 4v16",
    "M12 4l8 5-8 5-8-5zM4 14l8 5 8-5",
    "M12 3l8 4v5c0 5-3.4 8-8 9-4.6-1-8-4-8-9V7z",
  ];
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={paths[index] ?? paths[0]} />
    </svg>
  );
}

function NodeGlyph({ kind }: { kind: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      {kind.includes("Agent") || kind === "人工" ? (
        <path d="M8 2l1.7 3.3L13 7l-3.3 1.7L8 12l-1.7-3.3L3 7l3.3-1.7z" />
      ) : (
        <path d="M3 3h10v10H3zM6 6h4v4H6z" />
      )}
    </svg>
  );
}

function AgentSparkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2l2.2 7.8L22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2z" />
    </svg>
  );
}

function BoundaryIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3l9 16H3zM12 9v5m0 3v.1" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14m-5-5 5 5-5 5" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}
