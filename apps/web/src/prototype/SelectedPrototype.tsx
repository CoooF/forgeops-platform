import { useEffect, useMemo, useRef, useState } from "react";

import {
  capabilityCatalog,
  prototypeNavigation,
  prototypeNodes,
  syntheticRun,
  type PrototypeNode,
  type PrototypeView,
} from "./prototype-fixture";
import "./selected-prototype.css";

const viewIds = new Set<PrototypeView>(
  prototypeNavigation.map((item) => item.id),
);

function initialView(): PrototypeView {
  const value = new URLSearchParams(window.location.search).get("view");
  return viewIds.has(value as PrototypeView)
    ? (value as PrototypeView)
    : "studio";
}

export function SelectedPrototype() {
  const [view, setView] = useState<PrototypeView>(initialView);
  const [selectedNodeId, setSelectedNodeId] = useState("planner-agent");
  const [agentOpen, setAgentOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [debugTab, setDebugTab] = useState("端口发射");
  const [studioLibrary, setStudioLibrary] = useState<"nodes" | "resources">(
    "nodes",
  );
  const agentCloseRef = useRef<HTMLButtonElement>(null);

  const selectedNode = useMemo(
    () =>
      prototypeNodes.find((item) => item.id === selectedNodeId) ??
      prototypeNodes[0],
    [selectedNodeId],
  );

  useEffect(() => {
    if (!agentOpen) return;
    agentCloseRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAgentOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [agentOpen]);

  function navigate(next: PrototypeView) {
    setView(next);
    setMobileNavOpen(false);
    const url = new URL(window.location.href);
    url.searchParams.set("view", next);
    window.history.replaceState({}, "", url);
  }

  return (
    <main className="prototype-root">
      <a className="prototype-skip" href="#prototype-content">
        跳到主要内容
      </a>
      <BoundaryBar />
      <header className="prototype-topbar">
        <button
          className="mobile-nav-trigger"
          aria-label="打开产品导航"
          aria-expanded={mobileNavOpen}
          onClick={() => {
            setMobileNavOpen((open) => !open);
          }}
        >
          <MenuIcon />
        </button>
        <Brand />
        <div className="project-crumb">
          <span>合成协同实验室</span>
          <b>/</b>
          <strong>订单与资源协调</strong>
          <small>LOCAL</small>
        </div>
        <div className="topbar-actions">
          <button className="search-button" aria-label="搜索原型内容">
            <SearchIcon />
            <span>搜索</span>
            <kbd>⌘ K</kbd>
          </button>
          <button
            className="main-agent-top"
            aria-label="打开主 Agent 项目协作层"
            onClick={() => {
              setAgentOpen(true);
            }}
          >
            <AgentIcon />
            <span>
              <small>项目协调层</small>主 Agent
            </span>
          </button>
        </div>
      </header>

      <div className="prototype-layout">
        <ProductSidebar
          view={view}
          open={mobileNavOpen}
          onNavigate={navigate}
          onClose={() => {
            setMobileNavOpen(false);
          }}
        />
        <section className="prototype-content" id="prototype-content">
          {view === "project" && (
            <ProjectView
              onNavigate={navigate}
              onOpenAgent={() => {
                setAgentOpen(true);
              }}
            />
          )}
          {view === "studio" && (
            <StudioView
              selectedNode={selectedNode}
              selectedNodeId={selectedNodeId}
              library={studioLibrary}
              debugTab={debugTab}
              onLibraryChange={setStudioLibrary}
              onSelectNode={setSelectedNodeId}
              onDebugTabChange={setDebugTab}
              onOpenAgent={() => {
                setAgentOpen(true);
              }}
            />
          )}
          {view === "runs" && <RunsView />}
          {view === "data" && <DataView />}
          {view === "agents" && <AgentsView />}
          {view === "domains" && <DomainsView />}
          {view === "governance" && <GovernanceView />}
        </section>
      </div>

      <button
        className="main-agent-fab"
        onClick={() => {
          setAgentOpen(true);
        }}
      >
        <AgentIcon />
        <span>主 Agent</span>
        <small>规划与解释</small>
      </button>
      {agentOpen && (
        <MainAgentPanel
          closeRef={agentCloseRef}
          onClose={() => {
            setAgentOpen(false);
          }}
          onOpenDraft={() => {
            setAgentOpen(false);
            navigate("studio");
          }}
        />
      )}
    </main>
  );
}

function BoundaryBar() {
  return (
    <header className="prototype-boundary" data-testid="prototype-boundary">
      <strong>EPIC—02.7 / 方向 A</strong>
      <span>高保真交互原型</span>
      <span>本地合成 fixture</span>
      <span>未接 Workflow / Run / Agent 后端</span>
      <b>ADVISORY · NOT EXECUTED</b>
      <a href="/">返回真实 API 页面</a>
    </header>
  );
}

function Brand() {
  return (
    <div className="prototype-brand" aria-label="ForgeOps">
      <ForgeMark />
      <span>
        <strong>ForgeOps</strong>
        <small>INDUSTRIAL INTELLIGENCE</small>
      </span>
    </div>
  );
}

function ProductSidebar({
  view,
  open,
  onNavigate,
  onClose,
}: {
  view: PrototypeView;
  open: boolean;
  onNavigate: (view: PrototypeView) => void;
  onClose: () => void;
}) {
  return (
    <>
      {open && (
        <button
          className="mobile-nav-scrim"
          aria-label="关闭产品导航"
          onClick={onClose}
        />
      )}
      <nav
        className={`prototype-sidebar ${open ? "open" : ""}`}
        aria-label="ForgeOps 产品区域"
      >
        <header>
          <span>产品区域</span>
          <small>项目 Scope</small>
        </header>
        {prototypeNavigation.map((item, index) => (
          <button
            key={item.id}
            className={view === item.id ? "active" : ""}
            aria-current={view === item.id ? "page" : undefined}
            onClick={() => {
              onNavigate(item.id);
            }}
          >
            <NavIcon index={index} />
            <span>
              <strong>{item.label}</strong>
              <small>{item.short}</small>
            </span>
            <em className={`source-${item.source.replaceAll(" ", "-")}`}>
              {item.source === "本地原型" ? "原型" : item.source}
            </em>
          </button>
        ))}
        <footer>
          <span>DOMAIN LOCK</span>
          <strong>协调基础域 @ 0.2</strong>
          <small>真实 API 可查看 · 原型不修改</small>
        </footer>
      </nav>
    </>
  );
}

function PageHeading({
  eyebrow,
  title,
  description,
  source,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  source: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <span>{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="page-heading-actions">
        <em>{source}</em>
        {actions}
      </div>
    </header>
  );
}

function ProjectView({
  onNavigate,
  onOpenAgent,
}: {
  onNavigate: (view: PrototypeView) => void;
  onOpenAgent: () => void;
}) {
  return (
    <div className="page-view project-view">
      <PageHeading
        eyebrow="PROJECT / SYNTHETIC COLLAB LAB"
        title="订单与资源协调"
        description="从项目目标进入工作，不把治理对象当作首页。真实项目边界保留，任务与风险为本地原型。"
        source="混合边界"
        actions={<button onClick={onOpenAgent}>请主 Agent 拆解目标</button>}
      />
      <section className="project-status-strip" aria-label="项目状态">
        <div>
          <span>领域锁</span>
          <strong>协调基础域 @ 0.2</strong>
          <small>真实 API</small>
        </div>
        <div>
          <span>工作流草稿</span>
          <strong>07 / 未持久化</strong>
          <small>本地原型</small>
        </div>
        <div>
          <span>最近推演</span>
          <strong>等待人工</strong>
          <small>合成状态</small>
        </div>
        <div>
          <span>Evidence</span>
          <strong>11 / 12</strong>
          <small>合成状态</small>
        </div>
      </section>
      <div className="project-grid">
        <section className="project-primary-task">
          <header>
            <span>当前任务</span>
            <em>本地原型</em>
          </header>
          <h2>评估订单变化对资源承诺的影响</h2>
          <p>
            主 Agent 负责解释目标和提出 Builder 草稿；三个执行 Agent
            在工作流内各自持有独立 Skill/MCP 装配。
          </p>
          <ol>
            <li>
              <b>01</b>
              <span>确认输入快照与数据质量</span>
              <em>有 1 个缺口</em>
            </li>
            <li>
              <b>02</b>
              <span>检查执行 Agent 的工具与权限</span>
              <em>待授权</em>
            </li>
            <li>
              <b>03</b>
              <span>查看候选、风险和 Evidence</span>
              <em>未执行</em>
            </li>
          </ol>
          <button
            onClick={() => {
              onNavigate("studio");
            }}
          >
            进入工作流工作室 <ArrowIcon />
          </button>
        </section>
        <aside className="project-side-list">
          <header>
            <span>需要关注</span>
            <small>3 ITEMS</small>
          </header>
          <button
            onClick={() => {
              onNavigate("agents");
            }}
          >
            <strong>候选方案 Agent 尚未授权模型</strong>
            <span>检查节点级 Skill / MCP 与权限</span>
          </button>
          <button
            onClick={() => {
              onNavigate("runs");
            }}
          >
            <strong>合成 Run 等待人工</strong>
            <span>比较 3 个候选与证据缺口</span>
          </button>
          <button
            onClick={() => {
              onNavigate("domains");
            }}
          >
            <strong>DomainLock 可追溯</strong>
            <span>查看 Registry、Installation 与版本锁</span>
          </button>
        </aside>
      </div>
    </div>
  );
}

function StudioView({
  selectedNode,
  selectedNodeId,
  library,
  debugTab,
  onLibraryChange,
  onSelectNode,
  onDebugTabChange,
  onOpenAgent,
}: {
  selectedNode: PrototypeNode;
  selectedNodeId: string;
  library: "nodes" | "resources";
  debugTab: string;
  onLibraryChange: (value: "nodes" | "resources") => void;
  onSelectNode: (id: string) => void;
  onDebugTabChange: (value: string) => void;
  onOpenAgent: () => void;
}) {
  return (
    <div className="studio-view">
      <header className="studio-commandbar">
        <div>
          <span>WORKFLOW / DRAFT 07</span>
          <strong>订单协调工作流</strong>
        </div>
        <dl>
          <div>
            <dt>DomainLock</dt>
            <dd>协调基础域 @ 0.2</dd>
          </div>
          <div>
            <dt>保存</dt>
            <dd>仅浏览器内存</dd>
          </div>
          <div>
            <dt>环境</dt>
            <dd>LOCAL PROTOTYPE</dd>
          </div>
        </dl>
        <div className="studio-actions">
          <button>原型校验</button>
          <button disabled>发布</button>
          <button disabled>运行</button>
        </div>
      </header>
      <div className="studio-layout">
        <aside className="studio-library" aria-label="节点与能力库">
          <div className="library-tabs" role="tablist" aria-label="节点库类型">
            <button
              role="tab"
              aria-selected={library === "nodes"}
              onClick={() => {
                onLibraryChange("nodes");
              }}
            >
              节点
            </button>
            <button
              role="tab"
              aria-selected={library === "resources"}
              onClick={() => {
                onLibraryChange("resources");
              }}
            >
              能力
            </button>
          </div>
          {library === "nodes" ? <NodeLibrary /> : <ResourceLibrary />}
        </aside>
        <section className="prototype-canvas" aria-label="高保真工作流画布">
          <div className="canvas-toolbar">
            <span>结构</span>
            <button aria-label="缩小">−</button>
            <b>78%</b>
            <button aria-label="放大">＋</button>
            <button>适应视图</button>
          </div>
          <svg
            className="prototype-connectors"
            viewBox="0 0 1000 560"
            aria-hidden="true"
          >
            <path d="M145 285 H230 V170 H310" />
            <path d="M145 285 H230 V395 H310" />
            <path d="M455 170 H545" />
            <path d="M455 395 H500 V170 H545" />
            <path d="M690 170 H760 V285 H835" />
            <path d="M690 395 H760 V285 H835" />
            <path d="M905 335 V440" />
          </svg>
          {prototypeNodes.map((node, index) => (
            <PrototypeNodeCard
              key={node.id}
              node={node}
              index={index}
              selected={node.id === selectedNodeId}
              onSelect={onSelectNode}
            />
          ))}
          <div className="canvas-corner-boundary">
            <BoundaryIcon /> NOT EXECUTED
          </div>
        </section>
        <NodeInspector node={selectedNode} onOpenAgent={onOpenAgent} />
        <DebugPanel
          selectedNode={selectedNode}
          activeTab={debugTab}
          onTabChange={onDebugTabChange}
        />
      </div>
    </div>
  );
}

function NodeLibrary() {
  const groups = [
    ["触发与输入", "事件触发器", "数据产品", "质量门"],
    ["理解与转换", "语义解析", "知识检索", "数据转换"],
    ["执行与决策", "执行 Agent", "算法", "仿真", "人工评审"],
    ["输出", "结果收集器", "页面输出", "报告导出"],
  ];
  return (
    <div className="library-list">
      {groups.map(([group, ...items]) => (
        <section key={group}>
          <header>{group}</header>
          {items.map((item) => (
            <button key={item}>
              <NodeMiniIcon />
              <span>{item}</span>
              <b>＋</b>
            </button>
          ))}
        </section>
      ))}
    </div>
  );
}

function ResourceLibrary() {
  return (
    <div className="resource-library">
      <p>Skill 与 MCP 不能直接拖到画布；请先选择执行 Agent，再装配到该节点。</p>
      {capabilityCatalog.map((item) => (
        <button key={`${item.kind}-${item.name}`}>
          <span>{item.kind}</span>
          <strong>{item.name}</strong>
          <small>
            v{item.version} · {item.trust}
          </small>
          <b>装配</b>
        </button>
      ))}
    </div>
  );
}

function PrototypeNodeCard({
  node,
  index,
  selected,
  onSelect,
}: {
  node: PrototypeNode;
  index: number;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      className={`prototype-node prototype-node-${String(index)} type-${node.type} ${selected ? "selected" : ""}`}
      aria-pressed={selected}
      onClick={() => {
        onSelect(node.id);
      }}
    >
      <header>
        <NodeMiniIcon />
        <span>{node.kind}</span>
        <em>
          {node.state === "ready"
            ? "已配置"
            : node.state === "warning"
              ? "有缺口"
              : "草稿"}
        </em>
      </header>
      <strong>{node.title}</strong>
      <small>{node.description}</small>
      {node.assembly && (
        <div className="node-tools">
          <b>{node.assembly.skills.length} Skill</b>
          <b>{node.assembly.mcps.length} MCP</b>
          <b>{node.assembly.permissions.length} Scope</b>
        </div>
      )}
      <footer>
        <span>
          <i /> DATA
        </span>
        <span>
          CONTROL <i />
        </span>
      </footer>
    </button>
  );
}

function NodeInspector({
  node,
  onOpenAgent,
}: {
  node: PrototypeNode;
  onOpenAgent: () => void;
}) {
  return (
    <aside className="node-inspector" aria-label="节点检查器">
      <header>
        <span>节点检查器</span>
        <button aria-label="更多节点操作">•••</button>
      </header>
      <div className="inspector-title">
        <NodeMiniIcon />
        <div>
          <span>{node.kind}</span>
          <h2>{node.title}</h2>
        </div>
      </div>
      <nav role="tablist" aria-label="节点配置分区">
        <button role="tab" aria-selected="true">
          配置
        </button>
        <button role="tab" aria-selected="false">
          端口
        </button>
        <button role="tab" aria-selected="false">
          测试
        </button>
      </nav>
      <section className="inspector-section">
        <header>
          <span>Typed Ports</span>
          <small>
            {node.inputs.length + node.outputs.length + node.controls.length}
          </small>
        </header>
        <dl>
          <div>
            <dt>DATA 输入</dt>
            <dd>{node.inputs.length}</dd>
          </div>
          <div>
            <dt>DATA 输出</dt>
            <dd>{node.outputs.length}</dd>
          </div>
          <div>
            <dt>CONTROL</dt>
            <dd>{node.controls.length}</dd>
          </div>
        </dl>
      </section>
      {node.assembly ? (
        <section
          className="inspector-section agent-tooling"
          aria-label="执行 Agent 节点级装配"
        >
          <header>
            <span>节点级工具装配</span>
            <em>不继承</em>
          </header>
          <label>
            模型<strong>{node.assembly.model}</strong>
          </label>
          <ToolRows
            title="Skills"
            items={node.assembly.skills.map(
              (item) => `${item.name} · v${item.version}`,
            )}
            action="安装 Skill"
          />
          <ToolRows
            title="MCP Servers"
            items={node.assembly.mcps.map(
              (item) => `${item.name} · v${item.version}`,
            )}
            action="连接 MCP"
          />
          <label>
            节点权限<strong>{node.assembly.permissions.join(" · ")}</strong>
          </label>
          <label>
            预算<strong>{node.assembly.budget}</strong>
          </label>
          <p>
            <BoundaryIcon /> 这些配置只属于当前子 Agent
            节点；本原型不会安装、连接或调用工具。
          </p>
        </section>
      ) : (
        <section className="inspector-section non-agent">
          <strong>非 Agent 节点</strong>
          <p>不提供模型、Skill 或 MCP 装配槽。</p>
        </section>
      )}
      <button className="ask-main-agent" onClick={onOpenAgent}>
        请主 Agent 解释此配置 <ArrowIcon />
      </button>
    </aside>
  );
}

function ToolRows({
  title,
  items,
  action,
}: {
  title: string;
  items: string[];
  action: string;
}) {
  return (
    <div className="tool-rows">
      <span>{title}</span>
      {items.map((item) => (
        <b key={item}>
          {item}
          <i>节点私有</i>
        </b>
      ))}
      <button title="仅改变本地原型视图">＋ {action}</button>
    </div>
  );
}

function DebugPanel({
  selectedNode,
  activeTab,
  onTabChange,
}: {
  selectedNode: PrototypeNode;
  activeTab: string;
  onTabChange: (value: string) => void;
}) {
  const tabs = ["端口发射", "变量", "Evidence", "Trace", "错误", "结果"];
  return (
    <section className="debug-panel" aria-label="运行与调试控制台">
      <nav role="tablist" aria-label="调试台内容">
        {tabs.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => {
              onTabChange(tab);
            }}
          >
            {tab}
          </button>
        ))}
      </nav>
      <div>
        <span>已选节点</span>
        <strong>{selectedNode.title}</strong>
        <p>
          {activeTab === "Evidence"
            ? "0 条真实 Evidence；仅展示合成引用结构。"
            : activeTab === "错误"
              ? "失败出口已定义，但未产生真实错误。"
              : "尚无真实运行数据或 PortEmission。"}
        </p>
      </div>
      <dl>
        <div>
          <dt>DATA</dt>
          <dd>0 EMISSIONS</dd>
        </div>
        <div>
          <dt>CONTROL</dt>
          <dd>NOT EXECUTED</dd>
        </div>
      </dl>
    </section>
  );
}

function RunsView() {
  const [runTab, setRunTab] = useState("路径");
  return (
    <div className="page-view runs-view">
      <PageHeading
        eyebrow={`RUN / ${syntheticRun.id}`}
        title="运行调查与候选比较"
        description="连续查看实际路径、节点输入输出、候选、Evidence、风险与人工待办；所有状态均来自本地合成 fixture。"
        source="本地合成 · 未运行"
        actions={<button disabled>要求重算</button>}
      />
      <section className="run-summary">
        <div>
          <span>状态</span>
          <strong>{syntheticRun.status}</strong>
        </div>
        <div>
          <span>实际路径</span>
          <strong>5 / 7 节点</strong>
        </div>
        <div>
          <span>候选</span>
          <strong>3</strong>
        </div>
        <div>
          <span>Evidence</span>
          <strong>11 / 12</strong>
        </div>
        <b>ADVISORY · NOT EXECUTED</b>
      </section>
      <nav className="run-tabs" role="tablist" aria-label="运行调查分区">
        {["路径", "候选比较", "Evidence", "Trace", "结果"].map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={runTab === tab}
            onClick={() => {
              setRunTab(tab);
            }}
          >
            {tab}
          </button>
        ))}
      </nav>
      <div className="run-investigation-grid">
        <section className="run-path">
          <header>
            <span>合成实际路径</span>
            <small>5 STEPS</small>
          </header>
          {syntheticRun.path.map((step, index) => (
            <div key={step}>
              <b>{String(index + 1).padStart(2, "0")}</b>
              <i />
              <span>
                <strong>{step}</strong>
                <small>{index === 4 ? "等待人工" : "合成完成"}</small>
              </span>
            </div>
          ))}
        </section>
        <section className="candidate-comparison">
          <header>
            <span>{runTab}</span>
            <small>可追溯比较</small>
          </header>
          {syntheticRun.candidates.map((candidate) => (
            <article key={candidate.id}>
              <b>{candidate.id}</b>
              <div>
                <strong>{candidate.title}</strong>
                <span>Evidence {candidate.evidence}</span>
              </div>
              <dl>
                <div>
                  <dt>综合分</dt>
                  <dd>{candidate.score}</dd>
                </div>
                <div>
                  <dt>风险</dt>
                  <dd>{candidate.risk}</dd>
                </div>
              </dl>
              <button>查看依据</button>
            </article>
          ))}
        </section>
        <aside className="evidence-ledger">
          <header>
            <span>Evidence Ledger</span>
            <small>合成引用</small>
          </header>
          <div>
            <b>WorkflowVersion</b>
            <span>draft-07 / 未持久化</span>
          </div>
          <div>
            <b>DomainLock</b>
            <span>协调基础域 @ 0.2</span>
          </div>
          <div>
            <b>ContextManifest</b>
            <span>ctx-syn-014</span>
          </div>
          <div>
            <b>Agent / Skill / MCP</b>
            <span>3 节点 · 5 Skills · 5 MCP bindings</span>
          </div>
          <div>
            <b>人工操作</b>
            <span>等待项目负责人批注</span>
          </div>
          <p>
            <BoundaryIcon /> 缺少 1 项数据时效 Evidence，不能形成“已执行”结论。
          </p>
        </aside>
      </div>
    </div>
  );
}

function DataView() {
  return (
    <div className="page-view data-view">
      <PageHeading
        eyebrow="DATA / CATALOG"
        title="数据与知识"
        description="连接、结构、质量、快照和证据在同一信息架构中；只有语义、知识与 Context 为真实 API。"
        source="混合边界"
      />
      <section className="source-explainer">
        <strong>来源边界</strong>
        <span>
          <i className="real" /> 真实 API
        </span>
        <span>
          <i className="prototype" /> 本地原型
        </span>
        <span>
          <i className="future" /> 未来能力
        </span>
      </section>
      <div className="management-grid">
        <ManagementSection
          title="连接"
          code="01"
          items={[
            ["数据源与数据库实例", "本地原型"],
            ["凭据引用", "未来能力"],
            ["连接健康", "未来能力"],
          ]}
        />
        <ManagementSection
          title="结构"
          code="02"
          items={[
            ["Catalog / Schema", "本地原型"],
            ["表与字段目录", "本地原型"],
            ["数据血缘", "未来能力"],
          ]}
        />
        <ManagementSection
          title="数据产品"
          code="03"
          items={[
            ["数据产品责任人", "本地原型"],
            ["质量规则与 SLA", "未来能力"],
            ["输入快照", "未来能力"],
          ]}
        />
        <ManagementSection
          title="语义与证据"
          code="04"
          items={[
            ["语义与知识", "真实 API"],
            ["ContextManifest", "真实 API"],
            ["Evidence 索引", "未来能力"],
          ]}
        />
      </div>
      <aside className="data-safety">
        <BoundaryIcon />
        <div>
          <strong>不会采集数据库凭据</strong>
          <p>
            连接、Schema、质量与快照仅为产品框架，不执行连接测试，也不显示伪造健康状态。
          </p>
        </div>
        <a href="/">打开真实语义 / 知识页面</a>
      </aside>
    </div>
  );
}

function ManagementSection({
  title,
  code,
  items,
}: {
  title: string;
  code: string;
  items: string[][];
}) {
  return (
    <section className="management-section">
      <header>
        <b>{code}</b>
        <h2>{title}</h2>
      </header>
      {items.map(([name, source]) => (
        <button key={name}>
          <span>
            <strong>{name}</strong>
            <small>
              {source === "真实 API" ? "可在现有页面验证" : "未接对应后端"}
            </small>
          </span>
          <em>{source}</em>
          <ArrowIcon />
        </button>
      ))}
    </section>
  );
}

function AgentsView() {
  return (
    <div className="page-view agents-view">
      <PageHeading
        eyebrow="AGENTS / NODE ASSEMBLY"
        title="Agent 与能力"
        description="执行 Agent Profile 是工作流节点模板；实际模型、Skill、MCP、权限和预算在每个节点实例上独立装配。"
        source="本地原型"
      />
      <section className="agent-architecture-note">
        <div>
          <AgentIcon />
          <span>
            <strong>主 Agent</strong>
            <small>目标理解 · 规划 · 协调 · Builder 草稿 · 解释</small>
          </span>
          <em>无执行端口</em>
        </div>
        <ArrowIcon />
        <div>
          <NodeMiniIcon />
          <span>
            <strong>执行 Agent 节点</strong>
            <small>独立模型 · 独立 Skill/MCP · 节点权限 · 失败出口</small>
          </span>
          <em>typed ports</em>
        </div>
      </section>
      <div className="agent-management-grid">
        <section className="agent-profiles">
          <header>
            <span>执行 Agent 节点实例</span>
            <small>3 INSTANCES</small>
          </header>
          {prototypeNodes
            .filter((node) => node.assembly)
            .map((node) => (
              <article key={node.id}>
                <header>
                  <NodeMiniIcon />
                  <div>
                    <strong>{node.title}</strong>
                    <span>{node.assembly?.model}</span>
                  </div>
                  <em>{node.state === "draft" ? "待授权" : "已配置"}</em>
                </header>
                <dl>
                  <div>
                    <dt>Skills</dt>
                    <dd>{node.assembly?.skills.length}</dd>
                  </div>
                  <div>
                    <dt>MCP</dt>
                    <dd>{node.assembly?.mcps.length}</dd>
                  </div>
                  <div>
                    <dt>Scopes</dt>
                    <dd>{node.assembly?.permissions.length}</dd>
                  </div>
                </dl>
                <div className="profile-tools">
                  {node.assembly?.skills.map((item) => (
                    <b key={item.name}>{item.name}</b>
                  ))}
                  {node.assembly?.mcps.map((item) => (
                    <b key={item.name}>{item.name}</b>
                  ))}
                </div>
                <button>
                  查看节点装配 <ArrowIcon />
                </button>
              </article>
            ))}
        </section>
        <aside className="capability-catalog">
          <header>
            <span>企业能力目录</span>
            <em>未来能力</em>
          </header>
          <p>
            目录提供可审核版本；“安装”只会创建某个执行 Agent
            节点的绑定草稿，不影响主 Agent。
          </p>
          {capabilityCatalog.map((item) => (
            <div key={`${item.kind}-${item.name}`}>
              <b>{item.kind}</b>
              <span>
                <strong>{item.name}</strong>
                <small>
                  v{item.version} · {item.trust}
                </small>
              </span>
              <button disabled>安装到节点</button>
            </div>
          ))}
        </aside>
      </div>
    </div>
  );
}

function DomainsView() {
  return (
    <div className="page-view domains-view">
      <PageHeading
        eyebrow="DOMAIN / CONTROLLED SEMANTICS"
        title="领域中心"
        description="把 Registry、组织安装、项目 DomainLock、Overlay 与影响分析组织为连续任务；真实 API 行为保持不变。"
        source="真实 API + 原型入口"
      />
      <div className="domain-flow">
        <ManagementSection
          code="01"
          title="Registry"
          items={[
            ["协调基础域 0.2", "真实 API"],
            ["包版本与撤回状态", "真实 API"],
          ]}
        />
        <ManagementSection
          code="02"
          title="组织安装"
          items={[
            ["Installation 与授权", "真实 API"],
            ["Overlay 配置", "本地原型"],
          ]}
        />
        <ManagementSection
          code="03"
          title="项目 DomainLock"
          items={[
            ["当前锁与历史", "真实 API"],
            ["升级影响分析", "真实 API"],
          ]}
        />
      </div>
      <aside className="data-safety">
        <BoundaryIcon />
        <div>
          <strong>领域操作仍由后端权限决定</strong>
          <p>原型不会绕过 Scope、跨组织隔离、包撤回和版本冲突。</p>
        </div>
        <a href="/">打开真实领域页面</a>
      </aside>
    </div>
  );
}

function GovernanceView() {
  return (
    <div className="page-view governance-view">
      <PageHeading
        eyebrow="GOVERNANCE / PROJECT SCOPE"
        title="权限与审计"
        description="成员、Scope 与项目审计来自真实 API；环境策略、Agent 工具授权和企业身份只展示产品入口。"
        source="混合边界"
      />
      <div className="governance-table" role="table" aria-label="治理能力边界">
        <header role="row">
          <span>能力</span>
          <span>当前来源</span>
          <span>强制边界</span>
          <span>入口</span>
        </header>
        {[
          ["成员与 Scope", "真实 API", "后端授权真值", "打开真实页面"],
          ["项目审计", "真实 API", "追加式审计证据", "打开真实页面"],
          ["Agent 节点工具授权", "本地原型", "每个节点独立 Scope", "查看原型"],
          ["环境与运行策略", "本地原型", "禁止伪造发布/运行", "查看框架"],
          ["企业身份与策略发布", "未来能力", "未验证 OIDC/SCIM", "不可用"],
        ].map((row) => (
          <div role="row" key={row[0]}>
            {row.map((cell, index) =>
              index === 3 ? (
                <button key={cell} disabled={cell === "不可用"}>
                  {cell}
                </button>
              ) : (
                <span key={cell}>{cell}</span>
              ),
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function MainAgentPanel({
  closeRef,
  onClose,
  onOpenDraft,
}: {
  closeRef: React.RefObject<HTMLButtonElement | null>;
  onClose: () => void;
  onOpenDraft: () => void;
}) {
  return (
    <div className="main-agent-scrim" onMouseDown={onClose}>
      <aside
        className="main-agent-panel"
        role="dialog"
        aria-modal="true"
        aria-label="主 Agent 项目协作层"
        onMouseDown={(event) => {
          event.stopPropagation();
        }}
      >
        <header>
          <AgentIcon />
          <div>
            <strong>主 Agent</strong>
            <span>项目级规划与解释 · 不参与具体执行</span>
          </div>
          <button
            ref={closeRef}
            aria-label="关闭主 Agent 面板"
            onClick={onClose}
          >
            <CloseIcon />
          </button>
        </header>
        <div className="main-agent-boundary">
          <BoundaryIcon />
          <p>
            <strong>没有 DATA / CONTROL 端口</strong>不安装或调用执行节点的
            Skill/MCP；不持有生产写权限；当前未调用模型。
          </p>
        </div>
        <section>
          <span>目标理解</span>
          <h2>评估订单变化对资源承诺的影响，并形成可追溯建议。</h2>
          <p>需要先确认输入快照时效、领域锁版本和候选方案 Agent 的模型授权。</p>
        </section>
        <section className="agent-plan">
          <span>建议步骤</span>
          <ol>
            <li>
              <b>01</b>
              <p>校验数据质量与 ContextManifest</p>
            </li>
            <li>
              <b>02</b>
              <p>为三个执行 Agent 分别检查 Skill、MCP 与 Scope</p>
            </li>
            <li>
              <b>03</b>
              <p>生成 Builder 草稿并由用户确认</p>
            </li>
            <li>
              <b>04</b>
              <p>进入合成 Run 调查，不执行工业系统动作</p>
            </li>
          </ol>
        </section>
        <section className="builder-diff">
          <header>
            <span>Builder 草稿 diff</span>
            <em>本地内存</em>
          </header>
          <p>
            <b>＋</b> 风险评估 Agent / 证据索引 MCP
          </p>
          <p>
            <b>＋</b> 失败出口 → 人工评审
          </p>
          <p>
            <b>!</b> 候选方案 Agent 模型待授权
          </p>
        </section>
        <footer>
          <button onClick={onOpenDraft}>查看工作流草稿</button>
          <small>不会写入 Workflow 后端</small>
        </footer>
      </aside>
    </div>
  );
}

function ForgeMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 4h16v16H4zM8 8h8M8 12h5M8 16h8" />
    </svg>
  );
}
function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}
function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="6" />
      <path d="m16 16 4 4" />
    </svg>
  );
}
function AgentIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}
function NodeMiniIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="5" width="14" height="14" rx="2" />
      <path d="M9 9h6M9 13h4" />
    </svg>
  );
}
function BoundaryIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m12 3 9 16H3zM12 9v4M12 16h.01" />
    </svg>
  );
}
function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}
function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m6 6 12 12M18 6 6 18" />
    </svg>
  );
}
function NavIcon({ index }: { index: number }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4" y="4" width="16" height="16" rx={index % 3} />
      <path
        d={
          index % 2
            ? "M8 9h8M8 13h5M8 17h8"
            : "M8 8h3v3H8zM13 8h3v3h-3zM8 13h3v3H8zM13 13h3v3h-3z"
        }
      />
    </svg>
  );
}
