import { useMemo, useState } from "react";

import {
  capabilityGroups,
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

function initialDirection(): DirectionId {
  const value = new URLSearchParams(window.location.search).get("direction");
  return directionIds.has(value as DirectionId)
    ? (value as DirectionId)
    : "precision";
}

export function DesignDirections() {
  const [direction, setDirection] = useState<DirectionId>(initialDirection);
  const [selectedNodeId, setSelectedNodeId] = useState("agent");
  const [consoleTab, setConsoleTab] = useState("端口发射");
  const [agentOpen, setAgentOpen] = useState(false);
  const [productModuleId, setProductModuleId] =
    useState<ProductModuleId>("workflows");
  const [modulePreviewOpen, setModulePreviewOpen] = useState(false);
  const selectedNode = useMemo(
    () => nodes.find((node) => node.id === selectedNodeId) ?? nodes[0],
    [selectedNodeId],
  );
  const current = directions.find((item) => item.id === direction) ?? {
    id: "precision" as const,
    code: "A",
    name: "精密工业工作台",
    thesis: "工程图式秩序 · 高密度长时操作",
  };
  const libraryCopy = {
    precision: ["节点与能力", "当前 DomainLock 可见", "搜索节点、端口或能力"],
    semantic: ["领域结构树", "按语义层级与依赖组织", "搜索概念、关系或能力"],
    investigation: [
      "路径与调查工具",
      "按风险、证据和出口筛选",
      "搜索路径、证据或节点",
    ],
  }[direction];
  const inspectorTitle = {
    precision: "节点检查器",
    semantic: "语义属性册",
    investigation: "节点调查卷宗",
  }[direction];
  const selectedProductModule =
    productModules.find((item) => item.id === productModuleId) ??
    productModules[1];

  function chooseDirection(next: DirectionId) {
    setDirection(next);
    const url = new URL(window.location.href);
    url.searchParams.set("direction", next);
    window.history.replaceState({}, "", url);
  }

  return (
    <main className={`direction-preview direction-${direction}`}>
      <header className="preview-gate" data-testid="prototype-boundary">
        <div>
          <strong>视觉方向预览</strong>
          <span>EPIC-02.7 · 等待产品负责人选择</span>
        </div>
        <div className="gate-boundaries">
          <span>本地合成</span>
          <span>交互原型</span>
          <span>未接 Workflow / Run / Agent 后端</span>
          <span>未运行 · 建议未执行</span>
        </div>
        <a href="/" title="返回现有真实 API 页面">
          真实治理页面 ↗
        </a>
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
            <b>{item.code}</b>
            <span>{item.name}</span>
            <small>{item.thesis}</small>
          </button>
        ))}
      </nav>

      <section className="studio-shell" data-testid={`direction-${direction}`}>
        <header className="studio-context">
          <div className="studio-brand">
            <span className="forge-mark">F</span>
            <b>ForgeOps</b>
            <small>工作流工作室</small>
          </div>
          <nav className="context-crumb" aria-label="项目上下文">
            <span>合成协同实验室</span>
            <i>/</i>
            <strong>订单与资源协调</strong>
            <i>/</i>
            <span>协调建议流程</span>
          </nav>
          <div className="lock-context">
            <span>领域锁</span>
            <strong>协调基础域 @ 0.2</strong>
            <em>状态正常</em>
          </div>
          <div className="draft-state">
            <span>草稿 07</span>
            <small>仅浏览器内存</small>
          </div>
          <div className="studio-actions">
            <button className="text-action">原型校验</button>
            <button className="run-action" disabled title="未接 Run 后端">
              运行（未接后端）
            </button>
          </div>
        </header>

        <nav className="global-product-nav" aria-label="ForgeOps 产品模块">
          <div className="product-nav-head">
            <span>产品</span>
            <small>LOCAL</small>
          </div>
          {productModules.map((item) => (
            <button
              key={item.id}
              className={productModuleId === item.id ? "active" : ""}
              aria-pressed={productModuleId === item.id}
              onClick={() => {
                setProductModuleId(item.id);
                setModulePreviewOpen(item.id !== "workflows");
              }}
            >
              <i>{item.icon}</i>
              <span>{item.name}</span>
              <small>{item.short}</small>
              <em
                className={
                  item.source === "真实 API"
                    ? "source-real"
                    : item.source === "混合边界"
                      ? "source-mixed"
                      : "source-prototype"
                }
              >
                {item.source}
              </em>
            </button>
          ))}
        </nav>

        <aside className="activity-rail" aria-label="工作室工具">
          {["库", "纲", "史", "版", "搜"].map((item, index) => (
            <button
              key={item}
              className={index === 0 ? "active" : ""}
              title={item}
            >
              {item}
            </button>
          ))}
          <span />
          <button title="设置">设</button>
        </aside>

        <aside className="capability-library">
          <div className="panel-title">
            <div>
              <strong>{libraryCopy[0]}</strong>
              <small>{libraryCopy[1]}</small>
            </div>
            <button aria-label="关闭节点库">‹</button>
          </div>
          <label className="capability-search">
            <span>⌕</span>
            <input aria-label="搜索节点" placeholder={libraryCopy[2]} />
            <kbd>⌘ K</kbd>
          </label>
          <div className="capability-groups">
            {capabilityGroups.map((group) => (
              <section key={group.name}>
                <h3>{group.name}</h3>
                {group.items.map((item, index) => (
                  <button key={item}>
                    <i className={`capability-icon icon-${String(index)}`} />
                    <span>{item}</span>
                    <small>{index % 2 === 0 ? "已安装" : "可用"}</small>
                    <b>＋</b>
                  </button>
                ))}
              </section>
            ))}
          </div>
        </aside>

        <section className="canvas-area" aria-label={`${current.name}画布`}>
          <div className="canvas-meta">
            <div>
              <b>{current.code}</b>
              <span>{current.name}</span>
              <small>{current.thesis}</small>
            </div>
            <div className="canvas-tools">
              <button title="撤销">↶</button>
              <button title="重做">↷</button>
              <i />
              <button title="缩小">−</button>
              <span>82%</span>
              <button title="放大">＋</button>
              <button title="适应视图">适应</button>
            </div>
          </div>
          {direction === "semantic" && (
            <div className="semantic-lanes" aria-hidden="true">
              <span>01 · 事件与数据</span>
              <span>02 · 语义与上下文</span>
              <span>03 · 推演与决策</span>
              <span>04 · 评审与结果</span>
            </div>
          )}
          {direction === "investigation" && (
            <div className="trace-ruler" aria-label="合成运行轨迹预览">
              <span>路径预览</span>
              <b>未运行</b>
              <i />
              <small>这里仅演示未来 Evidence / Trace 层级</small>
            </div>
          )}
          <EdgeLayer direction={direction} />
          <div className="nodes-layer">
            {nodes.map((node) => (
              <NodeCard
                key={node.id}
                node={node}
                direction={direction}
                selected={node.id === selectedNodeId}
                onSelect={setSelectedNodeId}
              />
            ))}
          </div>
          <div className="canvas-legend">
            <span>
              <i className="data-port" />
              DATA 数据端口
            </span>
            <span>
              <i className="control-port" />
              CONTROL 控制端口
            </span>
            <span>
              <i className="edge-sample" />
              仅展示预期连线 · 未执行
            </span>
          </div>
        </section>

        <aside className="inspector-panel">
          <div className="panel-title inspector-title">
            <div>
              <small>{inspectorTitle}</small>
              <strong>{selectedNode?.title}</strong>
            </div>
            <button aria-label="关闭检查器">×</button>
          </div>
          <nav className="inspector-tabs">
            <button className="active">配置</button>
            <button>端口</button>
            <button>权限</button>
            <button>测试</button>
          </nav>
          <div className="inspector-body">
            <div className="source-callout">
              <span>原型配置</span>
              <strong>未写入 Workflow 后端</strong>
            </div>
            <label>
              节点名称
              <input value={selectedNode?.title ?? ""} readOnly />
            </label>
            <label>
              能力版本
              <select value="locked" disabled>
                <option value="locked">当前领域锁固定版本</option>
              </select>
            </label>
            <section className="port-inspection">
              <h3>类型化端口</h3>
              <div>
                <i className="data-port" />
                <span>结构化建议</span>
                <code>DATA · OUTPUT</code>
              </div>
              <div>
                <i className="data-port" />
                <span>依据引用</span>
                <code>DATA · OUTPUT</code>
              </div>
              <div>
                <i className="control-port" />
                <span>待人工</span>
                <code>CONTROL</code>
              </div>
              <div className="port-warning">
                <i>!</i>
                <span>失败出口尚未连接</span>
                <b>阻断发布</b>
              </div>
            </section>
            <section className="inspector-facts">
              <div>
                <span>数据分类</span>
                <strong>合成内部数据</strong>
              </div>
              <div>
                <span>模型调用</span>
                <strong>未配置 / 未调用</strong>
              </div>
              <div>
                <span>工具权限</span>
                <strong>无外部写权限</strong>
              </div>
              <div>
                <span>预算</span>
                <strong>等待定义</strong>
              </div>
            </section>
          </div>
        </aside>

        <section className="debug-console">
          <header>
            <div className="debug-tabs">
              {[
                "运行",
                "端口发射",
                "实际分支",
                "Evidence",
                "Trace",
                "错误",
                "结果",
              ].map((tab) => (
                <button
                  key={tab}
                  className={consoleTab === tab ? "active" : ""}
                  onClick={() => {
                    setConsoleTab(tab);
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="debug-state">
              <i />
              未运行 <span>本地合成原型</span>
            </div>
          </header>
          <div className="console-content">
            <div className="console-empty">
              <b>{consoleTab}</b>
              <span>尚无真实运行数据</span>
              <small>
                连接 EPIC-03 Run / PortEmission 后端后，此处才显示事实。
              </small>
            </div>
            <div className="console-ledger">
              <span>WorkflowVersion</span>
              <code>未生成</code>
              <span>Run</span>
              <code>未创建</code>
              <span>Evidence</span>
              <code>未产生</code>
              <span>执行边界</span>
              <code>ADVISORY_NOT_EXECUTED</code>
            </div>
          </div>
        </section>

        {modulePreviewOpen && selectedProductModule && (
          <aside
            className="module-preview-drawer"
            role="dialog"
            aria-label={`${selectedProductModule.name}模块预览`}
          >
            <header>
              <div>
                <span>{selectedProductModule.source}</span>
                <h2>{selectedProductModule.name}</h2>
                <p>{selectedProductModule.description}</p>
              </div>
              <button
                aria-label="关闭模块预览"
                onClick={() => {
                  setModulePreviewOpen(false);
                }}
              >
                ×
              </button>
            </header>
            <div className="module-preview-items">
              {selectedProductModule.items.map((item) => (
                <button key={item.name} disabled>
                  <span>{item.name}</span>
                  <em className={`item-${item.state.replaceAll(" ", "-")}`}>
                    {item.state}
                  </em>
                </button>
              ))}
            </div>
            <footer>
              <strong>产品框架预览</strong>
              <span>未接对应后端 · 不产生数据库、Agent 或运行状态</span>
            </footer>
          </aside>
        )}

        <button
          className="main-agent-entry"
          aria-expanded={agentOpen}
          onClick={() => {
            setAgentOpen((value) => !value);
          }}
        >
          <span>主 Agent</span>
          <strong>{agentOpen ? "收起协作预览" : "协助拆解目标"}</strong>
          <small>未调用模型</small>
        </button>
        {agentOpen && (
          <aside
            className="agent-popover"
            role="dialog"
            aria-label="主 Agent 协作预览"
          >
            <header>
              <span>主 Agent / Builder</span>
              <b>协作层 · 非执行节点</b>
            </header>
            <p>我理解的目标：在订单变化后形成可追溯、需人工确认的协调建议。</p>
            <ol>
              <li>歧义术语“可用资源”仍需负责人澄清</li>
              <li>执行 Agent 的失败出口尚未连接</li>
              <li>建议先补 Evidence 最低要求，再做原型校验</li>
            </ol>
            <div>
              <span>未调用模型</span>
              <span>未修改草稿</span>
              <span>未运行</span>
            </div>
          </aside>
        )}
      </section>
    </main>
  );
}

function NodeCard({
  node,
  direction,
  selected,
  onSelect,
}: {
  node: StudioNode;
  direction: DirectionId;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      className={`studio-node node-${node.kind.replaceAll(" ", "-")} status-${node.status} ${selected ? "selected" : ""}`}
      style={nodePosition(node, direction)}
      onClick={() => {
        onSelect(node.id);
      }}
      aria-label={`选择节点：${node.title}`}
    >
      <span className="node-type">
        <i />
        {node.kind}
        <em>
          {node.status === "ready"
            ? "已配置"
            : node.status === "warning"
              ? "需澄清"
              : "草稿"}
        </em>
      </span>
      <strong>{node.title}</strong>
      <small>{node.subtitle}</small>
      <div className="node-ports">
        <span>
          {node.inputs.slice(0, 1).map((port) => (
            <i key={port} className="input-port" title={port} />
          ))}
        </span>
        <span>
          {node.outputs.slice(0, 2).map((port) => (
            <i key={port} className="output-port" title={port} />
          ))}
        </span>
      </div>
      <div className="node-control">
        <span>{node.control.slice(0, 2).join(" · ")}</span>
        <i title="控制端口" />
      </div>
    </button>
  );
}

function nodePosition(node: StudioNode, direction: DirectionId) {
  const semanticPositions: Record<string, [number, number]> = {
    trigger: [32, 105],
    quality: [32, 285],
    semantic: [240, 105],
    knowledge: [240, 285],
    agent: [448, 105],
    decision: [448, 285],
    human: [640, 105],
    collector: [640, 285],
  };
  const investigationPositions: Record<string, [number, number]> = {
    trigger: [30, 120],
    quality: [190, 120],
    semantic: [190, 295],
    knowledge: [350, 295],
    agent: [350, 120],
    decision: [510, 120],
    human: [650, 120],
    collector: [650, 295],
  };
  const selected =
    direction === "semantic"
      ? semanticPositions[node.id]
      : direction === "investigation"
        ? investigationPositions[node.id]
        : undefined;
  return { left: selected?.[0] ?? node.x, top: selected?.[1] ?? node.y };
}

function EdgeLayer({ direction }: { direction: DirectionId }) {
  if (direction === "semantic") {
    return (
      <svg
        className="edge-layer semantic-edges"
        viewBox="0 0 900 500"
        aria-hidden="true"
      >
        <path d="M109 233 V285" />
        <path d="M186 339 H214 V169 H240" />
        <path d="M317 233 V285" />
        <path d="M394 349 H422 V169 H448" />
        <path d="M525 233 V285" />
        <path d="M602 169 H640" />
        <path d="M602 349 H620 V169 H640" />
        <path className="control-edge" d="M717 233 V285" />
      </svg>
    );
  }
  if (direction === "investigation") {
    return (
      <svg
        className="edge-layer investigation-edges"
        viewBox="0 0 900 500"
        aria-hidden="true"
      >
        <path className="actual-path" d="M158 164 H190" />
        <path className="actual-path" d="M318 164 H350" />
        <path className="actual-path" d="M478 164 H510" />
        <path className="actual-path" d="M638 164 H650" />
        <path d="M254 208 V295" />
        <path d="M318 339 H350" />
        <path d="M414 295 V208" />
        <path d="M574 208 V339 H650" />
        <path className="control-edge" d="M714 208 V295" />
      </svg>
    );
  }
  return (
    <svg className="edge-layer" viewBox="0 0 900 480" aria-hidden="true">
      <path d="M176 154 C190 154 194 130 208 130" />
      <path d="M350 130 C368 130 370 130 390 130" />
      <path d="M350 174 C374 174 365 304 390 304" />
      <path d="M532 130 C555 130 540 214 566 214" />
      <path d="M532 304 C555 304 545 232 566 232" />
      <path d="M708 214 C716 214 674 130 682 130" />
      <path d="M708 232 C716 232 674 334 682 334" />
      <path className="control-edge" d="M824 180 C842 220 840 288 824 318" />
    </svg>
  );
}
