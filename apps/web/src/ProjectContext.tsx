import { useCallback, useEffect, useState } from "react";

import {
  api,
  describeApiError,
  type ContextManifest,
  type GroundingResult,
  type ProjectDomainLock,
  type SemanticComponentInventory,
  type SemanticQueryResult,
} from "./project-api";

const FIXED_EVALUATION_TIME = "2026-01-15T10:00:00Z";
const DEFAULT_MAPPING_SOURCE = JSON.stringify(
  {
    sourceSystem: "synthetic.catalog",
    refType: "record",
    objectRef: "entry",
    fieldRef: "kind",
    code: "ITEM",
  },
  null,
  2,
);
const DEFAULT_GROUNDING = JSON.stringify(
  {
    entityRefs: [],
    relationAssertions: [],
    mappingRefs: [],
    knowledgeCitations: [],
    declaredConstraintIds: [],
  },
  null,
  2,
);

export function ProjectContextPanel({
  actor,
  projectId,
  currentLock,
  canQuery,
  canCompile,
  canValidate,
}: {
  actor: string;
  projectId: string;
  currentLock: ProjectDomainLock | null;
  canQuery: boolean;
  canCompile: boolean;
  canValidate: boolean;
}) {
  const [inventory, setInventory] = useState<SemanticComponentInventory | null>(
    null,
  );
  const [history, setHistory] = useState<ContextManifest[]>([]);
  const [selectedManifest, setSelectedManifest] =
    useState<ContextManifest | null>(null);
  const [term, setTerm] = useState("目录项");
  const [termResult, setTermResult] = useState<SemanticQueryResult | null>(
    null,
  );
  const [mappingSource, setMappingSource] = useState(DEFAULT_MAPPING_SOURCE);
  const [mappingResult, setMappingResult] =
    useState<SemanticQueryResult | null>(null);
  const [purpose, setPurpose] = useState("OWNER_REVIEW");
  const [requestedTerms, setRequestedTerms] = useState("目录项");
  const [semanticIds, setSemanticIds] = useState(
    "urn:forgeops:synthetic:catalog:collection\nurn:forgeops:synthetic:catalog:contains",
  );
  const [mappingIds, setMappingIds] = useState("catalog.mapping.item-primary");
  const [knowledgeIds, setKnowledgeIds] = useState("");
  const [maxItems, setMaxItems] = useState(30);
  const [maxChars, setMaxChars] = useState(20000);
  const [evaluationTime, setEvaluationTime] = useState(FIXED_EVALUATION_TIME);
  const [groundingJson, setGroundingJson] = useState(DEFAULT_GROUNDING);
  const [groundingResult, setGroundingResult] =
    useState<GroundingResult | null>(null);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    if (!projectId) return;
    setError("");
    try {
      const [components, manifests] = await Promise.all([
        api.projectSemanticComponents(actor, projectId),
        api.contextManifests(actor, projectId),
      ]);
      setInventory(components);
      setHistory(manifests.items);
      setSelectedManifest((current) =>
        current &&
        manifests.items.some(
          (item) => item.contextManifestId === current.contextManifestId,
        )
          ? current
          : (manifests.items.at(-1) ?? null),
      );
      setKnowledgeIds(
        (current) =>
          current ||
          components.components
            .flatMap((item) =>
              item.knowledgeVersionId ? [item.knowledgeVersionId] : [],
            )
            .join("\n"),
      );
    } catch (loadError) {
      setInventory(null);
      setHistory([]);
      setError(describeApiError(loadError));
    }
  }, [actor, projectId]);

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  async function perform(operation: () => Promise<void>, message: string) {
    setPending(true);
    setError("");
    setNotice("");
    try {
      await operation();
      setNotice(message);
    } catch (operationError) {
      setError(describeApiError(operationError));
    } finally {
      setPending(false);
    }
  }

  async function resolveTerm() {
    if (!term.trim()) return;
    await perform(async () => {
      setTermResult(
        await api.semanticQuery(actor, projectId, {
          queryType: "TERM",
          value: term,
          evaluationTime,
        }),
      );
    }, "术语解析完成；歧义和未知结果不会被自动替换。 ");
  }

  async function resolveMapping() {
    const source = parseObject(mappingSource, setError);
    if (!source) return;
    await perform(async () => {
      setMappingResult(
        await api.semanticQuery(actor, projectId, {
          queryType: "SOURCE_MAPPING",
          source,
          evaluationTime,
        }),
      );
    }, "Source mapping 已按当前 DomainLock 解析。 ");
  }

  async function compile() {
    await perform(async () => {
      const manifest = await api.compileContext(actor, projectId, {
        purpose,
        requestedTerms: splitRefs(requestedTerms),
        semanticIds: splitRefs(semanticIds),
        mappingIds: splitRefs(mappingIds),
        knowledgeVersionIds: splitRefs(knowledgeIds),
        budget: { maxItems, maxChars },
        locale: "zh-CN",
        evaluationTime,
      });
      setSelectedManifest(manifest);
      setGroundingResult(null);
      await reload();
      setSelectedManifest(manifest);
    }, "ContextManifest 已确定性编译并写入不可变历史。 ");
  }

  async function validateGrounding() {
    if (!selectedManifest) return;
    const candidate = parseObject(groundingJson, setError);
    if (!candidate) return;
    await perform(async () => {
      setGroundingResult(
        await api.validateGrounding(
          actor,
          selectedManifest.contextManifestId,
          candidate,
        ),
      );
    }, "结构化 Grounding 校验完成；未调用模型。 ");
  }

  return (
    <div
      className="detail-body context-panel"
      data-testid="project-context-page"
    >
      <div className="section-heading">
        <div>
          <h3>Context / Grounding</h3>
          <p>
            只使用当前 DomainLock 固定的已发布语义与知识版本；不执行 Agent、LLM
            或 Workflow。
          </p>
        </div>
        <span className="truth-chip">LOCAL_SYNTHETIC · NO MODEL</span>
      </div>

      {(notice || error) && (
        <div
          className={
            error ? "message error-message" : "message success-message"
          }
          role="status"
        >
          {error || notice}
        </div>
      )}

      {!currentLock ? (
        <div className="forbidden-state">
          当前项目没有
          DomainLock。先在“领域锁”页固定一个健康版本，语义查询和新上下文编译将保持关闭。
        </div>
      ) : (
        <section className="context-lock-summary">
          <div>
            <span>Current DomainLock</span>
            <strong>
              {currentLock.immutableFacts.rootPackageId}@
              {currentLock.immutableFacts.rootPackageVersion}
            </strong>
            <code>{currentLock.immutableFacts.lockDigest}</code>
          </div>
          <Status value={currentLock.derivedHealth.health} />
          <span>{inventory?.components.length ?? 0} 个锁定组件</span>
          <span>授权影响 NONE</span>
        </section>
      )}

      {currentLock?.derivedHealth.health === "AT_RISK" && (
        <div className="impact-warning">
          当前锁 AT_RISK：{currentLock.derivedHealth.reasons.join(" · ")}
          。后端会拒绝新查询和编译。
        </div>
      )}

      {inventory && (
        <section className="locked-components">
          <div className="section-heading">
            <div>
              <h4>锁定组件清单</h4>
              <p>
                版本、摘要和治理状态来自真实 Registry / Semantic / Knowledge
                表。
              </p>
            </div>
          </div>
          <div className="component-ledger">
            {inventory.components.map((item) => (
              <article key={item.packageVersionId}>
                <div>
                  <strong>{item.packageId}</strong>
                  <small>
                    {item.packageVersion} ·{" "}
                    {item.componentKind ?? "NON_SEMANTIC"}
                  </small>
                </div>
                <code>{shortDigest(item.contentDigest)}</code>
                <Status
                  value={
                    item.semanticStatus ?? item.knowledgeStatus ?? "LOCKED_ONLY"
                  }
                />
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="resolver-grid">
        <div className="context-card">
          <h4>Term Resolver</h4>
          <p>返回 RESOLVED / AMBIGUOUS / UNKNOWN；不会静默猜测。</p>
          <label>
            术语
            <input
              value={term}
              onChange={(event) => {
                setTerm(event.target.value);
              }}
            />
          </label>
          <button
            disabled={!canQuery || pending || !currentLock}
            onClick={() => void resolveTerm()}
          >
            解析术语
          </button>
          {termResult && <QueryResultView result={termResult} />}
        </div>
        <div className="context-card">
          <h4>Source Mapping Resolver</h4>
          <p>只接受结构化 source reference，不接受 SQL、JSONPath 或脚本。</p>
          <label>
            Source reference JSON
            <textarea
              rows={8}
              value={mappingSource}
              onChange={(event) => {
                setMappingSource(event.target.value);
              }}
            />
          </label>
          <button
            disabled={!canQuery || pending || !currentLock}
            onClick={() => void resolveMapping()}
          >
            解析映射
          </button>
          {mappingResult && <QueryResultView result={mappingResult} />}
        </div>
      </section>

      <section className="context-compiler">
        <div className="section-heading">
          <div>
            <h4>Context Compiler</h4>
            <p>
              显式 purpose、refs、有效时间和预算；同一请求生成相同 canonical
              digest。
            </p>
          </div>
        </div>
        <div className="compiler-fields">
          <label>
            Purpose
            <input
              value={purpose}
              onChange={(event) => {
                setPurpose(event.target.value);
              }}
            />
          </label>
          <label>
            固定评估时间
            <input
              value={evaluationTime}
              onChange={(event) => {
                setEvaluationTime(event.target.value);
              }}
            />
          </label>
          <label>
            Requested terms
            <textarea
              value={requestedTerms}
              onChange={(event) => {
                setRequestedTerms(event.target.value);
              }}
            />
          </label>
          <label>
            SemanticIds
            <textarea
              value={semanticIds}
              onChange={(event) => {
                setSemanticIds(event.target.value);
              }}
            />
          </label>
          <label>
            MappingIds
            <textarea
              value={mappingIds}
              onChange={(event) => {
                setMappingIds(event.target.value);
              }}
            />
          </label>
          <label>
            KnowledgeVersionIds
            <textarea
              value={knowledgeIds}
              onChange={(event) => {
                setKnowledgeIds(event.target.value);
              }}
            />
          </label>
          <label>
            Max items
            <input
              type="number"
              min={1}
              max={500}
              value={maxItems}
              onChange={(event) => {
                setMaxItems(Number(event.target.value));
              }}
            />
          </label>
          <label>
            Max chars
            <input
              type="number"
              min={1}
              max={100000}
              value={maxChars}
              onChange={(event) => {
                setMaxChars(Number(event.target.value));
              }}
            />
          </label>
        </div>
        <button
          disabled={!canCompile || pending || !currentLock}
          onClick={() => void compile()}
        >
          编译不可变 ContextManifest
        </button>
      </section>

      {selectedManifest && (
        <section
          className="manifest-investigation"
          data-testid="context-manifest-preview"
        >
          <div className="section-heading">
            <div>
              <h4>ContextManifest 调查视图</h4>
              <p>{selectedManifest.contextManifestId}</p>
            </div>
            <Status
              value={selectedManifest.truncated ? "TRUNCATED" : "COMPLETE"}
            />
          </div>
          <Digest
            label="Canonical digest"
            value={selectedManifest.canonicalDigest}
          />
          <div className="manifest-metrics">
            <span>语义 {selectedManifest.includedSemanticRefs.length}</span>
            <span>映射 {selectedManifest.includedMappingRefs.length}</span>
            <span>知识 {selectedManifest.includedKnowledgeRefs.length}</span>
            <span>未知 {selectedManifest.unresolvedTerms.length}</span>
            <span>歧义 {selectedManifest.ambiguousTerms.length}</span>
            <span>排除 {selectedManifest.excludedRefs.length}</span>
            <span>
              预算 {selectedManifest.budgetUsage.items} items /{" "}
              {selectedManifest.budgetUsage.chars} chars
            </span>
          </div>
          {selectedManifest.excludedRefs.length > 0 && (
            <div className="exclusion-list">
              {selectedManifest.excludedRefs.map((item) => (
                <span key={`${item.ref}-${item.reason}`}>
                  {item.reason} · {item.ref}
                </span>
              ))}
            </div>
          )}
          <details>
            <summary>查看完整 Manifest</summary>
            <pre className="json-viewer">
              {JSON.stringify(selectedManifest, null, 2)}
            </pre>
          </details>
        </section>
      )}

      <section className="grounding-grid">
        <div className="context-card">
          <h4>Grounding Validator</h4>
          <p>
            只验证结构化实体、关系、约束、映射与 citation 是否属于固定
            Manifest。
          </p>
          <label>
            Candidate JSON
            <textarea
              rows={12}
              value={groundingJson}
              onChange={(event) => {
                setGroundingJson(event.target.value);
              }}
            />
          </label>
          <button
            disabled={!canValidate || !selectedManifest || pending}
            onClick={() => void validateGrounding()}
          >
            运行结构校验
          </button>
          {groundingResult && (
            <div
              className={`grounding-result ${groundingResult.status.toLowerCase()}`}
            >
              <Status value={groundingResult.status} />
              <code>{groundingResult.digest}</code>
              <p>{groundingResult.issues.join(" · ") || "无结构化问题"}</p>
              <small>modelCalled = false</small>
            </div>
          )}
        </div>
        <div className="context-card">
          <h4>不可变 Context 历史</h4>
          <p>升级 DomainLock 不会改写旧 Manifest；历史仅供调查。</p>
          <div className="context-history">
            {history.length === 0 ? (
              <div className="empty-state">尚未编译上下文。</div>
            ) : (
              history.map((item) => (
                <button
                  key={item.contextManifestId}
                  className={
                    selectedManifest?.contextManifestId ===
                    item.contextManifestId
                      ? "selected"
                      : ""
                  }
                  onClick={() => {
                    setSelectedManifest(item);
                  }}
                >
                  <span>
                    <strong>{item.purpose}</strong>
                    <small>{item.compiledAt}</small>
                  </span>
                  <code>{shortDigest(item.canonicalDigest)}</code>
                </button>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function QueryResultView({ result }: { result: SemanticQueryResult }) {
  const refs =
    result.status === "RESOLVED" ? result.canonicalRefs : result.candidates;
  return (
    <div className={`query-result ${result.status.toLowerCase()}`}>
      <Status value={result.status} />
      <span>{result.issues.join(" · ") || "规范引用已解析"}</span>
      {refs.map((item) => (
        <article key={`${item.refId}-${item.packageVersionId}`}>
          <strong>{item.semanticId ?? item.refId}</strong>
          <small>
            {item.packageId}@{item.packageVersion}
          </small>
          <code>{shortDigest(item.payloadDigest)}</code>
        </article>
      ))}
    </div>
  );
}

function Status({ value }: { value: string }) {
  return <span className={`state-badge ${value.toLowerCase()}`}>{value}</span>;
}

function Digest({ label, value }: { label: string; value: string }) {
  return (
    <div className="semantic-digest">
      <span>{label}</span>
      <code>{value}</code>
    </div>
  );
}

function splitRefs(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseObject(
  value: string,
  setError: (message: string) => void,
): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(value);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      setError("JSON 顶层必须是对象。");
      return null;
    }
    return parsed as Record<string, unknown>;
  } catch {
    setError("请输入严格结构化 JSON；不会解析 Prompt、脚本或模板。");
    return null;
  }
}

function shortDigest(value: string): string {
  return value.length > 28 ? `${value.slice(0, 18)}…${value.slice(-8)}` : value;
}
