import { useCallback, useEffect, useMemo, useState } from "react";

import {
  api,
  describeApiError,
  type FdsPackageVersion,
  type KnowledgeAsset,
  type KnowledgeVersion,
  type SemanticImpact,
  type SemanticPayload,
} from "./project-api";

type SemanticView =
  | "namespaces"
  | "concepts"
  | "terms"
  | "relations"
  | "constraints"
  | "mappings";

const VIEW_LABELS: Record<SemanticView, string> = {
  namespaces: "命名空间",
  concepts: "概念",
  terms: "术语",
  relations: "关系",
  constraints: "约束",
  mappings: "映射",
};

export function SemanticKnowledge({
  actor,
  organizationId,
  canManage,
}: {
  actor: string;
  organizationId: string;
  canManage: boolean;
}) {
  const [payloads, setPayloads] = useState<SemanticPayload[]>([]);
  const [assets, setAssets] = useState<KnowledgeAsset[]>([]);
  const [components, setComponents] = useState<FdsPackageVersion[]>([]);
  const [impacts, setImpacts] = useState<SemanticImpact[]>([]);
  const [selectedPayloadId, setSelectedPayloadId] = useState("");
  const [semanticView, setSemanticView] = useState<SemanticView>("concepts");
  const [packageVersionId, setPackageVersionId] = useState("");
  const [payloadJson, setPayloadJson] = useState("");
  const [reason, setReason] = useState("本地合成语义治理核验");
  const [assetTitle, setAssetTitle] = useState("");
  const [assetId, setAssetId] = useState("");
  const [knowledgePackageId, setKnowledgePackageId] = useState("");
  const [knowledgeJson, setKnowledgeJson] = useState("");
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [selectedImpact, setSelectedImpact] = useState<SemanticImpact | null>(
    null,
  );
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const selectedPayload = payloads.find(
    (item) => item.semanticPayloadId === selectedPayloadId,
  );
  const semanticComponents = components.filter((item) =>
    ["ONTOLOGY", "TERMINOLOGY", "DATA_MAPPING"].includes(
      item.immutableFacts.componentKind ?? "",
    ),
  );
  const knowledgeComponents = components.filter(
    (item) => item.immutableFacts.componentKind === "KNOWLEDGE",
  );
  const versions = useMemo(
    () => assets.flatMap((item) => item.versions),
    [assets],
  );

  const reload = useCallback(async () => {
    if (!organizationId) {
      setPayloads([]);
      setAssets([]);
      return;
    }
    setError("");
    try {
      const [semantic, knowledge, registry, impactReports] = await Promise.all([
        api.semanticPayloads(actor, organizationId),
        api.knowledgeAssets(actor, organizationId),
        api.fdsPackageVersions(actor, { kind: "COMPONENT" }),
        api.semanticImpacts(actor),
      ]);
      setPayloads(semantic.items);
      setAssets(knowledge.items);
      setComponents(registry.items);
      setImpacts(impactReports.items);
      setSelectedPayloadId((current) =>
        semantic.items.some((item) => item.semanticPayloadId === current)
          ? current
          : (semantic.items[0]?.semanticPayloadId ?? ""),
      );
      setAssetId((current) =>
        knowledge.items.some((item) => item.assetId === current)
          ? current
          : (knowledge.items[0]?.assetId ?? ""),
      );
    } catch (loadError) {
      setPayloads([]);
      setAssets([]);
      setComponents([]);
      setError(describeApiError(loadError));
    }
  }, [actor, organizationId]);

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

  async function submitSemanticPayload() {
    const definition = parseObject(payloadJson, setError);
    if (!definition || !packageVersionId) return;
    await perform(async () => {
      const created = await api.registerSemanticPayload(
        actor,
        packageVersionId,
        definition,
      );
      setPayloadJson("");
      await reload();
      setSelectedPayloadId(created.semanticPayloadId);
    }, "语义 payload 已按精确 Registry 组件版本登记并完成摘要校验。");
  }

  async function transitionPayload(
    payload: SemanticPayload,
    transition: "publish" | "withdraw",
  ) {
    await perform(
      async () => {
        await api.transitionSemanticPayload(actor, payload, transition, reason);
        await reload();
      },
      `语义版本已${transition === "publish" ? "发布" : "撤回"}。`,
    );
  }

  async function createAsset() {
    if (!assetTitle.trim()) return;
    await perform(async () => {
      const created = await api.createKnowledgeAsset(actor, organizationId, {
        title: assetTitle,
        description: "由 Semantic & Knowledge 页面创建的本地合成知识容器",
        assetType: "TEXT",
        language: "zh-CN",
        owner: actor,
        reviewer: "local-reviewer",
      });
      setAssetTitle("");
      await reload();
      setAssetId(created.assetId);
    }, "KnowledgeAsset 已创建；内容版本仍需绑定精确 KNOWLEDGE 组件。");
  }

  async function registerKnowledgeVersion() {
    const body = parseObject(knowledgeJson, setError);
    if (!body || !assetId || !knowledgePackageId) return;
    await perform(async () => {
      await api.registerKnowledgeVersion(actor, assetId, {
        ...body,
        packageVersionId: knowledgePackageId,
      });
      setKnowledgeJson("");
      await reload();
    }, "不可变知识版本已写入对象存储并绑定 Registry 摘要。");
  }

  async function transitionKnowledge(
    version: KnowledgeVersion,
    transition: "publish" | "withdraw",
  ) {
    await perform(
      async () => {
        await api.transitionKnowledgeVersion(
          actor,
          version,
          transition,
          reason,
        );
        await reload();
      },
      `知识版本已${transition === "publish" ? "发布" : "撤回"}。`,
    );
  }

  async function analyzeImpact() {
    if (!fromId || !toId) return;
    await perform(async () => {
      const report = await api.analyzeSemanticImpact(
        actor,
        "SEMANTIC",
        fromId,
        toId,
      );
      setSelectedImpact(report);
      await reload();
    }, "结构化差异与 DomainLock 影响已生成；Workflow 影响仍未评估。");
  }

  const visibleDefinitions = selectedPayload
    ? selectedPayload.definition[semanticView]
    : [];

  return (
    <main
      className="workspace semantic-workspace"
      data-testid="semantic-knowledge-page"
    >
      <div className="workspace-heading registry-heading">
        <div>
          <p className="section-label">EPIC-02.6C / 版本化上下文事实</p>
          <h1>语义与知识</h1>
          <p>
            管理规范 ID、术语、关系、映射和不可变知识版本；所有查询按 Project
            DomainLock 限域。
          </p>
        </div>
        <div className="truth-stack" aria-label="语义运行时边界">
          <strong>LOCAL_SYNTHETIC</strong>
          <span>NOT_ENTERPRISE_VERIFIED</span>
          <span>NO AGENT · NO LLM · NO RAG</span>
        </div>
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

      <section className="semantic-summary" aria-label="语义资产摘要">
        <Metric label="语义版本" value={payloads.length} />
        <Metric label="知识容器" value={assets.length} />
        <Metric label="不可变知识版本" value={versions.length} />
        <Metric label="影响报告" value={impacts.length} />
      </section>

      <section className="semantic-grid">
        <div className="semantic-panel semantic-catalog">
          <div className="section-heading">
            <div>
              <h2>规范语义目录</h2>
              <p>选择版本后检查来源、摘要与声明式对象。</p>
            </div>
            <button className="quiet-button" onClick={() => void reload()}>
              刷新
            </button>
          </div>
          <div className="semantic-version-list">
            {payloads.length === 0 ? (
              <div className="empty-state">当前组织尚无可见语义版本。</div>
            ) : (
              payloads.map((item) => (
                <button
                  key={item.semanticPayloadId}
                  className={
                    item.semanticPayloadId === selectedPayloadId
                      ? "semantic-version selected"
                      : "semantic-version"
                  }
                  onClick={() => {
                    setSelectedPayloadId(item.semanticPayloadId);
                  }}
                >
                  <span>
                    <strong>{item.packageId}</strong>
                    <small>
                      {item.packageVersion} · {item.componentKind}
                    </small>
                  </span>
                  <Status value={item.status} />
                </button>
              ))
            )}
          </div>
          {selectedPayload && (
            <div className="semantic-definition">
              <div className="semantic-tabs" role="tablist">
                {(Object.keys(VIEW_LABELS) as SemanticView[]).map((item) => (
                  <button
                    key={item}
                    className={semanticView === item ? "active" : ""}
                    onClick={() => {
                      setSemanticView(item);
                    }}
                  >
                    {VIEW_LABELS[item]} ·{" "}
                    {selectedPayload.definition[item].length}
                  </button>
                ))}
              </div>
              <Digest
                label="Payload digest"
                value={selectedPayload.payloadDigest}
              />
              <p className="provenance-line">
                来源：{selectedPayload.provenanceRef}
              </p>
              <div className="definition-table">
                {visibleDefinitions.length === 0 ? (
                  <div className="empty-state">该版本没有此类声明。</div>
                ) : (
                  visibleDefinitions.map((item, index) => (
                    <details key={definitionKey(item, index)}>
                      <summary>{definitionTitle(item, index)}</summary>
                      <pre>{JSON.stringify(item, null, 2)}</pre>
                    </details>
                  ))
                )}
              </div>
              {canManage && (
                <div className="row-actions">
                  {selectedPayload.status === "VALIDATED_LOCAL_SYNTHETIC" && (
                    <button
                      disabled={pending}
                      onClick={() =>
                        void transitionPayload(selectedPayload, "publish")
                      }
                    >
                      发布本地合成版本
                    </button>
                  )}
                  {selectedPayload.status !== "WITHDRAWN" && (
                    <button
                      className="danger-button"
                      disabled={pending}
                      onClick={() =>
                        void transitionPayload(selectedPayload, "withdraw")
                      }
                    >
                      撤回版本
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="semantic-panel governance-panel">
          <div className="section-heading">
            <div>
              <h2>登记与版本治理</h2>
              <p>写入动作需要后端权限、幂等键和 If-Match。</p>
            </div>
          </div>
          {canManage ? (
            <div className="stacked-forms">
              <details open>
                <summary>登记 semantic payload</summary>
                <label>
                  精确 Registry Component version
                  <select
                    value={packageVersionId}
                    onChange={(event) => {
                      setPackageVersionId(event.target.value);
                    }}
                  >
                    <option value="">
                      选择 ONTOLOGY / TERMINOLOGY / DATA_MAPPING
                    </option>
                    {semanticComponents.map((item) => (
                      <option
                        key={item.packageVersionId}
                        value={item.packageVersionId}
                      >
                        {item.immutableFacts.packageId}@
                        {item.immutableFacts.packageVersion} ·
                        {item.immutableFacts.componentKind}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  严格 payload JSON
                  <textarea
                    rows={10}
                    value={payloadJson}
                    onChange={(event) => {
                      setPayloadJson(event.target.value);
                    }}
                    placeholder='{"schemaVersion":"forgeops.semantic/v1",...}'
                  />
                </label>
                <button
                  disabled={pending || !packageVersionId || !payloadJson}
                  onClick={() => void submitSemanticPayload()}
                >
                  校验并登记
                </button>
              </details>
              <label>
                治理原因
                <input
                  value={reason}
                  onChange={(event) => {
                    setReason(event.target.value);
                  }}
                />
              </label>
              <details>
                <summary>创建 KnowledgeAsset</summary>
                <label>
                  知识容器名称
                  <input
                    value={assetTitle}
                    onChange={(event) => {
                      setAssetTitle(event.target.value);
                    }}
                    placeholder="本地合成参考资料"
                  />
                </label>
                <button
                  disabled={pending || !assetTitle}
                  onClick={() => void createAsset()}
                >
                  创建治理容器
                </button>
              </details>
              <details>
                <summary>登记不可变 KnowledgeAssetVersion</summary>
                <label>
                  KnowledgeAsset
                  <select
                    value={assetId}
                    onChange={(event) => {
                      setAssetId(event.target.value);
                    }}
                  >
                    <option value="">选择知识容器</option>
                    {assets.map((item) => (
                      <option key={item.assetId} value={item.assetId}>
                        {item.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  精确 KNOWLEDGE Component version
                  <select
                    value={knowledgePackageId}
                    onChange={(event) => {
                      setKnowledgePackageId(event.target.value);
                    }}
                  >
                    <option value="">选择知识组件</option>
                    {knowledgeComponents.map((item) => (
                      <option
                        key={item.packageVersionId}
                        value={item.packageVersionId}
                      >
                        {item.immutableFacts.packageId}@
                        {item.immutableFacts.packageVersion}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  版本元数据与 content JSON
                  <textarea
                    rows={10}
                    value={knowledgeJson}
                    onChange={(event) => {
                      setKnowledgeJson(event.target.value);
                    }}
                    placeholder='{"versionLabel":"1.0.0","title":"...","sourceRef":"...","contentType":"text/plain","content":"..."}'
                  />
                </label>
                <button
                  disabled={
                    pending || !assetId || !knowledgePackageId || !knowledgeJson
                  }
                  onClick={() => void registerKnowledgeVersion()}
                >
                  写入不可变版本
                </button>
              </details>
            </div>
          ) : (
            <p className="read-only-note">
              当前身份只有查看权限；版本登记、发布和撤回由后端拒绝。
            </p>
          )}
        </div>
      </section>

      <section className="semantic-panel knowledge-section">
        <div className="section-heading">
          <div>
            <h2>KnowledgeAsset 与不可变版本</h2>
            <p>
              内容是未可信数据；来源、许可、分类、用途和有效期共同决定可用性。
            </p>
          </div>
        </div>
        <div className="knowledge-table">
          {assets.length === 0 ? (
            <div className="empty-state">当前组织尚无知识资产。</div>
          ) : (
            assets.flatMap((asset) =>
              asset.versions.length === 0
                ? [
                    <article key={asset.assetId}>
                      <div>
                        <strong>{asset.title}</strong>
                        <small>{asset.description}</small>
                      </div>
                      <Status value="NO_VERSION" />
                    </article>,
                  ]
                : asset.versions.map((version) => (
                    <article key={version.knowledgeVersionId}>
                      <div>
                        <strong>{version.title}</strong>
                        <small>
                          {version.packageId}@{version.packageVersion} ·{" "}
                          {version.owner} / {version.reviewer}
                        </small>
                      </div>
                      <span>
                        {version.contentClassification} ·{" "}
                        {version.allowedPurposes.join(", ")}
                      </span>
                      <code>{shortDigest(version.contentDigest)}</code>
                      <span>
                        {version.licenseId} ·{" "}
                        {formatPeriod(version.validFrom, version.validTo)}
                      </span>
                      <Status value={version.status} />
                      {canManage && version.status !== "WITHDRAWN" && (
                        <div className="row-actions">
                          {version.status === "VALIDATED_LOCAL_SYNTHETIC" && (
                            <button
                              className="quiet-button"
                              onClick={() =>
                                void transitionKnowledge(version, "publish")
                              }
                            >
                              发布
                            </button>
                          )}
                          <button
                            className="quiet-button"
                            onClick={() =>
                              void transitionKnowledge(version, "withdraw")
                            }
                          >
                            撤回
                          </button>
                        </div>
                      )}
                    </article>
                  )),
            )
          )}
        </div>
      </section>

      <section className="semantic-panel impact-section">
        <div className="section-heading">
          <div>
            <h2>版本差异与锁定影响</h2>
            <p>
              只分析语义/知识版本与受影响锁；Workflow impact 固定为
              NOT_EVALUATED。
            </p>
          </div>
        </div>
        <div className="impact-controls">
          <select
            aria-label="影响分析起始版本"
            value={fromId}
            onChange={(event) => {
              setFromId(event.target.value);
            }}
          >
            <option value="">From semantic version</option>
            {payloads.map((item) => (
              <option
                key={item.semanticPayloadId}
                value={item.semanticPayloadId}
              >
                {item.packageId}@{item.packageVersion}
              </option>
            ))}
          </select>
          <span>→</span>
          <select
            aria-label="影响分析目标版本"
            value={toId}
            onChange={(event) => {
              setToId(event.target.value);
            }}
          >
            <option value="">To semantic version</option>
            {payloads.map((item) => (
              <option
                key={item.semanticPayloadId}
                value={item.semanticPayloadId}
              >
                {item.packageId}@{item.packageVersion}
              </option>
            ))}
          </select>
          <button
            disabled={!fromId || !toId || pending}
            onClick={() => void analyzeImpact()}
          >
            生成影响报告
          </button>
        </div>
        {(selectedImpact ?? impacts.at(-1)) && (
          <pre className="json-viewer impact-result">
            {JSON.stringify(selectedImpact ?? impacts.at(-1), null, 2)}
          </pre>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value.toString().padStart(2, "0")}</strong>
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
    setError("请输入有效 JSON；不接受模板、脚本、URL fetch 或文件路径。");
    return null;
  }
}

function definitionKey(item: Record<string, unknown>, index: number): string {
  return (
    firstString(
      item.semanticId,
      item.termId,
      item.constraintId,
      item.mappingId,
    ) ?? index.toString()
  );
}

function definitionTitle(item: Record<string, unknown>, index: number): string {
  return (
    firstString(
      item.preferredLabel,
      item.preferredTerm,
      item.semanticId,
      item.constraintId,
      item.mappingId,
    ) ?? `声明 ${(index + 1).toString()}`
  );
}

function firstString(...values: unknown[]): string | undefined {
  return values.find((value): value is string => typeof value === "string");
}

function shortDigest(value: string): string {
  return value.length > 28 ? `${value.slice(0, 18)}…${value.slice(-8)}` : value;
}

function formatPeriod(from: string, to: string | null): string {
  return `${from.slice(0, 10)} → ${to ? to.slice(0, 10) : "持续有效"}`;
}
