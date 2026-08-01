import { useCallback, useEffect, useMemo, useState } from "react";

import {
  api,
  describeApiError,
  type DomainInstallation,
  type FdsPackageVersion,
  type PackageImpact,
} from "./project-api";

type Run = (operation: () => Promise<void>, success: string) => Promise<void>;

export function DomainRegistry({
  actor,
  organizationId,
  canRegisterPublic,
  canManageOrganization,
  pending,
  run,
  notice,
  error,
}: {
  actor: string;
  organizationId: string;
  canRegisterPublic: boolean;
  canManageOrganization: boolean;
  pending: boolean;
  run: Run;
  notice: string;
  error: string;
}) {
  const [packages, setPackages] = useState<FdsPackageVersion[]>([]);
  const [installations, setInstallations] = useState<DomainInstallation[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState("");
  const [selectedInstallationId, setSelectedInstallationId] = useState("");
  const [rootPackageVersionId, setRootPackageVersionId] = useState("");
  const [kind, setKind] = useState("");
  const [state, setState] = useState("");
  const [visibility, setVisibility] = useState("");
  const [manifestJson, setManifestJson] = useState("");
  const [reason, setReason] = useState("本地合成环境治理核验");
  const [preview, setPreview] = useState<DomainInstallation | null>(null);
  const [impact, setImpact] = useState<PackageImpact | null>(null);
  const [loadError, setLoadError] = useState("");

  const selectedPackage = packages.find(
    (item) => item.packageVersionId === selectedPackageId,
  );
  const selectedInstallation = installations.find(
    (item) => item.installationId === selectedInstallationId,
  );
  const installableRoots = useMemo(
    () =>
      packages.filter(
        (item) =>
          ["DOMAIN", "ORGANIZATION_OVERLAY"].includes(
            item.immutableFacts.kind,
          ) && item.governance.state === "REGISTERED_VALIDATED",
      ),
    [packages],
  );

  const reload = useCallback(async () => {
    setLoadError("");
    try {
      const [registry, organizationInstallations] = await Promise.all([
        api.fdsPackageVersions(actor, { kind, state, visibility }),
        organizationId
          ? api.domainInstallations(actor, organizationId)
          : Promise.resolve({ items: [], total: 0, limit: 100, offset: 0 }),
      ]);
      setPackages(registry.items);
      setInstallations(organizationInstallations.items);
      setSelectedPackageId((current) =>
        registry.items.some((item) => item.packageVersionId === current)
          ? current
          : (registry.items[0]?.packageVersionId ?? ""),
      );
      setSelectedInstallationId((current) =>
        organizationInstallations.items.some(
          (item) => item.installationId === current,
        )
          ? current
          : (organizationInstallations.items[0]?.installationId ?? ""),
      );
      setRootPackageVersionId((current) =>
        registry.items.some((item) => item.packageVersionId === current)
          ? current
          : "",
      );
    } catch (error) {
      setPackages([]);
      setInstallations([]);
      setLoadError(describeApiError(error));
    }
  }, [actor, kind, organizationId, state, visibility]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [reload]);

  async function registerManifest() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(manifestJson);
    } catch {
      setLoadError("Manifest 必须是有效的 JSON。 ");
      return;
    }
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      setLoadError("Manifest 顶层必须是 JSON 对象。 ");
      return;
    }
    const manifest = parsed as Record<string, unknown>;
    const owner =
      manifest.visibility === "ORGANIZATION_PRIVATE"
        ? organizationId
        : undefined;
    await run(async () => {
      await api.registerFdsPackageVersion(actor, manifest, owner);
      setManifestJson("");
      await reload();
    }, "FDS 能力包版本已通过后端严格校验并完成登记。 ");
  }

  async function transitionPackage(transition: "quarantine" | "withdraw") {
    if (!selectedPackage) return;
    await run(
      async () => {
        await api.transitionFdsPackageVersion(
          actor,
          selectedPackage,
          transition,
          reason,
        );
        await reload();
        setImpact(
          await api.fdsPackageImpacts(actor, selectedPackage.packageVersionId),
        );
      },
      `注册中心治理状态已更新：${transition === "withdraw" ? "撤回" : "隔离"}。`,
    );
  }

  async function previewInstallation() {
    if (!organizationId || !rootPackageVersionId) return;
    setLoadError("");
    try {
      setPreview(
        await api.previewDomainInstallation(
          actor,
          organizationId,
          rootPackageVersionId,
        ),
      );
    } catch (error) {
      setPreview(null);
      setLoadError(describeApiError(error));
    }
  }

  async function createInstallation() {
    if (!organizationId || !rootPackageVersionId) return;
    await run(async () => {
      const created = await api.createDomainInstallation(
        actor,
        organizationId,
        rootPackageVersionId,
      );
      setSelectedInstallationId(created.installationId);
      await reload();
    }, "领域组合已安装为“未启用”状态，不会创建运行能力。 ");
  }

  async function transitionInstallation(
    transition: "disable" | "revoke" | "logical-uninstall",
  ) {
    if (!selectedInstallation) return;
    await run(
      async () => {
        await api.transitionDomainInstallation(
          actor,
          selectedInstallation,
          transition,
          reason,
        );
        await reload();
      },
      `安装记录治理状态已更新：${installationTransitionLabel(transition)}。`,
    );
  }

  return (
    <main className="workspace registry-workspace">
      <div className="workspace-heading registry-heading">
        <div>
          <p className="section-label">FDS / 本地合成资产</p>
          <h1>领域资产注册中心</h1>
          <p>
            管理领域包的固定版本、组织安装、项目引用与撤回影响，全部状态来自真实接口和数据库。
          </p>
        </div>
        <div className="truth-stack" aria-label="FDS 可信边界">
          <strong>本地合成数据</strong>
          <span>尚未完成企业验证</span>
          <span>不会自动启用运行能力</span>
        </div>
      </div>

      {loadError && (
        <div className="message error-message" role="alert">
          {loadError}
        </div>
      )}
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

      <section className="registry-grid">
        <div className="registry-column">
          <div className="section-heading">
            <div>
              <h2>可见能力包版本</h2>
              <p>每次请求都会重新校验可见范围和治理状态。</p>
            </div>
            <button className="quiet-button" onClick={() => void reload()}>
              刷新
            </button>
          </div>
          <div className="registry-filters">
            <Filter label="类型" value={kind} setValue={setKind}>
              <option value="">全部类型</option>
              <option value="DOMAIN">领域包</option>
              <option value="ORGANIZATION_OVERLAY">组织扩展包</option>
              <option value="SCENARIO">场景包</option>
              <option value="COMPONENT">能力组件</option>
            </Filter>
            <Filter label="状态" value={state} setValue={setState}>
              <option value="">全部状态</option>
              <option value="REGISTERED_VALIDATED">已登记校验</option>
              <option value="QUARANTINED">已隔离</option>
              <option value="WITHDRAWN">已撤回</option>
            </Filter>
            <Filter
              label="可见范围"
              value={visibility}
              setValue={setVisibility}
            >
              <option value="">全部范围</option>
              <option value="PUBLIC">公开</option>
              <option value="PARTNER">合作伙伴</option>
              <option value="ORGANIZATION_PRIVATE">组织私有</option>
              <option value="PRIVATE">私有</option>
            </Filter>
          </div>
          <div className="registry-list" aria-label="FDS 能力包版本">
            {packages.length === 0 ? (
              <div className="empty-state">
                当前范围还没有可见的能力包版本。
              </div>
            ) : (
              packages.map((item) => (
                <button
                  key={item.packageVersionId}
                  className={
                    selectedPackageId === item.packageVersionId
                      ? "registry-card selected"
                      : "registry-card"
                  }
                  onClick={() => {
                    setSelectedPackageId(item.packageVersionId);
                    setImpact(null);
                  }}
                >
                  <span>
                    <strong>{item.immutableFacts.packageId}</strong>
                    <small>
                      {item.immutableFacts.packageVersion} ·{" "}
                      {kindLabel(item.immutableFacts.kind)}
                    </small>
                  </span>
                  <StateBadge state={item.governance.state} />
                </button>
              ))
            )}
          </div>
        </div>

        <div className="registry-column detail-column">
          {selectedPackage ? (
            <>
              <div className="section-heading">
                <div>
                  <p className="section-label">不可变版本事实</p>
                  <h2>{selectedPackage.immutableFacts.packageId}</h2>
                  <p>{selectedPackage.packageVersionId}</p>
                </div>
                <StateBadge state={selectedPackage.governance.state} />
              </div>
              <dl className="facts-grid compact-facts">
                <Fact
                  label="版本"
                  value={selectedPackage.immutableFacts.packageVersion}
                />
                <Fact
                  label="可见范围"
                  value={visibilityLabel(
                    selectedPackage.immutableFacts.visibility,
                  )}
                />
                <Fact
                  label="可信级别"
                  value={trustLabel(selectedPackage.immutableFacts.trustTier)}
                />
                <Fact
                  label="内容分类"
                  value={classificationLabel(
                    selectedPackage.immutableFacts.contentClassification,
                  )}
                />
                <Fact
                  label="发布方"
                  value={selectedPackage.immutableFacts.publisher}
                />
                <Fact
                  label="许可证"
                  value={`${selectedPackage.immutableFacts.licenseId} · ${
                    selectedPackage.immutableFacts.licenseVerified
                      ? "已核验"
                      : "未核验"
                  }`}
                />
              </dl>
              <Digest
                label="Manifest 摘要"
                value={selectedPackage.immutableFacts.manifestDigest}
              />
              <Digest
                label="内容摘要"
                value={selectedPackage.immutableFacts.contentDigest}
              />
              <details>
                <summary>查看 Manifest、依赖、权限与预算原始数据</summary>
                <pre className="json-viewer">
                  {JSON.stringify(
                    selectedPackage.immutableFacts.manifest,
                    null,
                    2,
                  )}
                </pre>
              </details>
              <div className="action-bar wrap-actions">
                <button
                  onClick={() =>
                    void api
                      .fdsPackageImpacts(
                        actor,
                        selectedPackage.packageVersionId,
                      )
                      .then(setImpact)
                      .catch((error: unknown) => {
                        setLoadError(describeApiError(error));
                      })
                  }
                >
                  查看引用影响
                </button>
                {(canRegisterPublic || canManageOrganization) &&
                  selectedPackage.governance.state !== "WITHDRAWN" && (
                    <>
                      {selectedPackage.governance.state ===
                        "REGISTERED_VALIDATED" && (
                        <button
                          disabled={pending}
                          onClick={() => void transitionPackage("quarantine")}
                        >
                          隔离版本
                        </button>
                      )}
                      <button
                        className="danger-button"
                        disabled={pending}
                        onClick={() => void transitionPackage("withdraw")}
                      >
                        撤回版本
                      </button>
                    </>
                  )}
              </div>
              {impact && (
                <div className="impact-panel" data-testid="package-impact">
                  <strong>引用影响</strong>
                  <span>{impact.installations.length} 个组织安装</span>
                  <span>{impact.projectDomainLocks.length} 个项目领域锁</span>
                  <small>历史记录保持不可变，系统不会自动切换项目版本。</small>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              选择左侧能力包版本后，可查看不可变事实与引用影响。
            </div>
          )}
        </div>
      </section>

      {(canRegisterPublic || canManageOrganization) && (
        <section className="registry-operation">
          <div className="section-heading">
            <div>
              <h2>登记本地合成 Manifest</h2>
              <p>
                JSON 会提交给后端严格校验，只有事务成功后才会成为正式注册记录。
              </p>
            </div>
          </div>
          <textarea
            aria-label="FDS manifest JSON"
            className="manifest-input"
            placeholder="粘贴本地合成 FDS Manifest JSON"
            value={manifestJson}
            onChange={(event) => {
              setManifestJson(event.target.value);
            }}
          />
          <div className="action-bar">
            <button
              disabled={pending || manifestJson.trim().length === 0}
              onClick={() => void registerManifest()}
            >
              校验并登记
            </button>
          </div>
        </section>
      )}

      <section className="registry-operation" aria-label="组织领域安装">
        <div className="section-heading">
          <div>
            <h2>组织领域安装</h2>
            <p>
              依赖解析只使用当前组织可见且有效的版本，并持久化固定
              DependencyLock。
            </p>
          </div>
        </div>
        {canManageOrganization ? (
          <div className="installation-controls">
            <label>
              选择领域包或组织扩展包
              <select
                aria-label="领域安装根包"
                value={rootPackageVersionId}
                onChange={(event) => {
                  setRootPackageVersionId(event.target.value);
                  setPreview(null);
                }}
              >
                <option value="">选择可安装版本</option>
                {installableRoots.map((item) => (
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
            <button
              disabled={!rootPackageVersionId || pending}
              onClick={() => void previewInstallation()}
            >
              预览依赖锁
            </button>
            <button
              disabled={!preview || pending}
              onClick={() => void createInstallation()}
            >
              安装为未启用
            </button>
          </div>
        ) : (
          <p className="read-only-note">当前身份只能查看组织安装记录。</p>
        )}
        {preview && (
          <LockSummary title="未提交的依赖预览" installation={preview} />
        )}
        <div className="installation-browser">
          <div className="registry-list">
            {installations.map((item) => (
              <button
                key={item.installationId}
                className={
                  item.installationId === selectedInstallationId
                    ? "registry-card selected"
                    : "registry-card"
                }
                onClick={() => {
                  setSelectedInstallationId(item.installationId);
                }}
              >
                <span>
                  <strong>{item.immutableFacts.rootPackageId}</strong>
                  <small>{shortDigest(item.immutableFacts.lockDigest)}</small>
                </span>
                <StateBadge state={item.installationState.state} />
              </button>
            ))}
          </div>
          {selectedInstallation && (
            <div>
              <LockSummary
                title="已持久化的安装依赖锁"
                installation={selectedInstallation}
              />
              {canManageOrganization && (
                <div className="action-bar wrap-actions">
                  {selectedInstallation.installationState.state ===
                    "INSTALLED_DISABLED" && (
                    <button
                      disabled={pending}
                      onClick={() => void transitionInstallation("disable")}
                    >
                      停用
                    </button>
                  )}
                  {!["REVOKED", "LOGICALLY_UNINSTALLED"].includes(
                    selectedInstallation.installationState.state,
                  ) && (
                    <button
                      disabled={pending}
                      onClick={() => void transitionInstallation("revoke")}
                    >
                      撤销
                    </button>
                  )}
                  {["DISABLED", "REVOKED"].includes(
                    selectedInstallation.installationState.state,
                  ) && (
                    <button
                      className="danger-button"
                      disabled={pending}
                      onClick={() =>
                        void transitionInstallation("logical-uninstall")
                      }
                    >
                      逻辑卸载
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <label className="governance-reason">
        治理操作原因
        <input
          value={reason}
          onChange={(event) => {
            setReason(event.target.value);
          }}
        />
      </label>
    </main>
  );
}

function Filter({
  label,
  value,
  setValue,
  children,
}: {
  label: string;
  value: string;
  setValue: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label>
      {label}
      <select
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
        }}
      >
        {children}
      </select>
    </label>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function Digest({ label, value }: { label: string; value: string }) {
  return (
    <div className="digest-row">
      <span>{label}</span>
      <code>{value}</code>
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  return (
    <span className={`state-badge ${state.toLowerCase()}`}>
      {stateLabel(state)}
    </span>
  );
}

function LockSummary({
  title,
  installation,
}: {
  title: string;
  installation: DomainInstallation;
}) {
  return (
    <div className="lock-summary">
      <div>
        <strong>{title}</strong>
        <StateBadge state={installation.derivedHealth.health} />
      </div>
      <Digest
        label="依赖锁摘要"
        value={installation.immutableFacts.lockDigest}
      />
      <div className="lock-nodes">
        {installation.immutableFacts.dependencyLock.nodes.map((node) => (
          <span key={`${node.packageId}-${node.packageVersion}`}>
            {node.packageId}@{node.packageVersion}
          </span>
        ))}
      </div>
      <small>不产生授权 · 未创建运行状态 · 语义运行时尚未启用</small>
    </div>
  );
}

function kindLabel(kind: string): string {
  return (
    {
      DOMAIN: "领域包",
      ORGANIZATION_OVERLAY: "组织扩展包",
      SCENARIO: "场景包",
      COMPONENT: "能力组件",
    }[kind] ?? kind
  );
}

function visibilityLabel(visibility: string): string {
  return (
    {
      PUBLIC: "公开",
      PARTNER: "合作伙伴可见",
      ORGANIZATION_PRIVATE: "组织私有",
      PRIVATE: "私有",
    }[visibility] ?? visibility
  );
}

function trustLabel(trust: string): string {
  return (
    {
      FIRST_PARTY_LOCAL: "本地第一方",
      THIRD_PARTY_UNVERIFIED: "第三方未核验",
    }[trust] ?? trust
  );
}

function classificationLabel(classification: string): string {
  return (
    {
      PUBLIC: "公开内容",
      INTERNAL: "内部内容",
      CONFIDENTIAL: "机密内容",
      RESTRICTED: "受限内容",
    }[classification] ?? classification
  );
}

function installationTransitionLabel(transition: string): string {
  return (
    {
      disable: "停用",
      revoke: "撤销",
      "logical-uninstall": "逻辑卸载",
    }[transition] ?? transition
  );
}

function stateLabel(state: string): string {
  return (
    {
      REGISTERED_VALIDATED: "已登记校验",
      QUARANTINED: "已隔离",
      WITHDRAWN: "已撤回",
      INSTALLED_DISABLED: "已安装未启用",
      DISABLED: "已停用",
      REVOKED: "已撤销",
      LOGICALLY_UNINSTALLED: "已逻辑卸载",
      HEALTHY_FOR_SELECTION: "状态正常",
      AT_RISK: "存在风险",
      BLOCKED_FOR_NEW_USE: "禁止新使用",
    }[state] ?? state
  );
}

function shortDigest(value: string): string {
  return value.length > 24 ? `${value.slice(0, 16)}…${value.slice(-8)}` : value;
}
