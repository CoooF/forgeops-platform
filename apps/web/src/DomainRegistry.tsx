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
  const [reason, setReason] = useState("Synthetic governance review");
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
      setLoadError("Manifest input must be valid JSON.");
      return;
    }
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      setLoadError("Manifest input must be a JSON object.");
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
    }, "FDS package version registered from the strict server validator.");
  }

  async function transitionPackage(transition: "quarantine" | "withdraw") {
    if (!selectedPackage) return;
    await run(async () => {
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
    }, `Registry governance state changed to ${transition.toUpperCase()}.`);
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
    }, "Installation persisted as INSTALLED_DISABLED; no runtime was enabled.");
  }

  async function transitionInstallation(
    transition: "disable" | "revoke" | "logical-uninstall",
  ) {
    if (!selectedInstallation) return;
    await run(async () => {
      await api.transitionDomainInstallation(
        actor,
        selectedInstallation,
        transition,
        reason,
      );
      await reload();
    }, `Installation governance transition ${transition} persisted.`);
  }

  return (
    <main className="workspace registry-workspace">
      <div className="workspace-heading registry-heading">
        <div>
          <p className="section-label">FDS / LOCAL SYNTHETIC REGISTRY</p>
          <h1>Domain Registry</h1>
          <p>
            Immutable package facts, organization installations, and withdrawal
            impact from the real API and database.
          </p>
        </div>
        <div className="truth-stack" aria-label="FDS truth boundary">
          <strong>LOCAL_SYNTHETIC</strong>
          <span>NOT_ENTERPRISE_VERIFIED</span>
          <span>Runtime capability not enabled</span>
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
              <h2>Visible package versions</h2>
              <p>Visibility and governance are evaluated on every request.</p>
            </div>
            <button className="quiet-button" onClick={() => void reload()}>
              Refresh
            </button>
          </div>
          <div className="registry-filters">
            <Filter label="Kind" value={kind} setValue={setKind}>
              <option value="">All kinds</option>
              <option>DOMAIN</option>
              <option>ORGANIZATION_OVERLAY</option>
              <option>SCENARIO</option>
              <option>COMPONENT</option>
            </Filter>
            <Filter label="State" value={state} setValue={setState}>
              <option value="">All states</option>
              <option>REGISTERED_VALIDATED</option>
              <option>QUARANTINED</option>
              <option>WITHDRAWN</option>
            </Filter>
            <Filter
              label="Visibility"
              value={visibility}
              setValue={setVisibility}
            >
              <option value="">All visibility</option>
              <option>PUBLIC</option>
              <option>PARTNER</option>
              <option>ORGANIZATION_PRIVATE</option>
              <option>PRIVATE</option>
            </Filter>
          </div>
          <div className="registry-list" aria-label="FDS package versions">
            {packages.length === 0 ? (
              <div className="empty-state">No package version is visible.</div>
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
                      {item.immutableFacts.kind}
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
                  <p className="section-label">IMMUTABLE FACTS</p>
                  <h2>{selectedPackage.immutableFacts.packageId}</h2>
                  <p>{selectedPackage.packageVersionId}</p>
                </div>
                <StateBadge state={selectedPackage.governance.state} />
              </div>
              <dl className="facts-grid compact-facts">
                <Fact
                  label="Version"
                  value={selectedPackage.immutableFacts.packageVersion}
                />
                <Fact
                  label="Visibility"
                  value={selectedPackage.immutableFacts.visibility}
                />
                <Fact
                  label="Trust tier"
                  value={selectedPackage.immutableFacts.trustTier}
                />
                <Fact
                  label="Classification"
                  value={selectedPackage.immutableFacts.contentClassification}
                />
                <Fact
                  label="Publisher"
                  value={selectedPackage.immutableFacts.publisher}
                />
                <Fact
                  label="License"
                  value={`${selectedPackage.immutableFacts.licenseId} · verified=${String(
                    selectedPackage.immutableFacts.licenseVerified,
                  )}`}
                />
              </dl>
              <Digest
                label="Manifest digest"
                value={selectedPackage.immutableFacts.manifestDigest}
              />
              <Digest
                label="Content digest"
                value={selectedPackage.immutableFacts.contentDigest}
              />
              <details>
                <summary>
                  Manifest, dependencies, permissions, and budget
                </summary>
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
                  View impact
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
                          Quarantine
                        </button>
                      )}
                      <button
                        className="danger-button"
                        disabled={pending}
                        onClick={() => void transitionPackage("withdraw")}
                      >
                        Withdraw
                      </button>
                    </>
                  )}
              </div>
              {impact && (
                <div className="impact-panel" data-testid="package-impact">
                  <strong>Reference impact</strong>
                  <span>{impact.installations.length} installations</span>
                  <span>{impact.projectDomainLocks.length} project locks</span>
                  <small>
                    Historical records remain immutable; no automatic switch
                    occurred.
                  </small>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              Select a package version for immutable facts.
            </div>
          )}
        </div>
      </section>

      {(canRegisterPublic || canManageOrganization) && (
        <section className="registry-operation">
          <div className="section-heading">
            <div>
              <h2>Register synthetic JSON</h2>
              <p>
                The browser submits JSON to the strict API; it does not become a
                Registry record until the transaction commits.
              </p>
            </div>
          </div>
          <textarea
            aria-label="FDS manifest JSON"
            className="manifest-input"
            placeholder="Paste a synthetic FDS manifest JSON object"
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
              Validate and register
            </button>
          </div>
        </section>
      )}

      <section
        className="registry-operation"
        aria-label="Organization installations"
      >
        <div className="section-heading">
          <div>
            <h2>Organization installation</h2>
            <p>
              Dependency resolution uses only visible, available Registry
              versions and persists a fixed DependencyLock.
            </p>
          </div>
        </div>
        {canManageOrganization ? (
          <div className="installation-controls">
            <label>
              DOMAIN or ORGANIZATION_OVERLAY root
              <select
                aria-label="Installation root"
                value={rootPackageVersionId}
                onChange={(event) => {
                  setRootPackageVersionId(event.target.value);
                  setPreview(null);
                }}
              >
                <option value="">Select an available root</option>
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
              Preview lock
            </button>
            <button
              disabled={!preview || pending}
              onClick={() => void createInstallation()}
            >
              Install disabled
            </button>
          </div>
        ) : (
          <p className="read-only-note">
            Organization installation is read-only for this actor.
          </p>
        )}
        {preview && (
          <LockSummary title="Uncommitted preview" installation={preview} />
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
                title="Persisted installation lock"
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
                      Disable
                    </button>
                  )}
                  {!["REVOKED", "LOGICALLY_UNINSTALLED"].includes(
                    selectedInstallation.installationState.state,
                  ) && (
                    <button
                      disabled={pending}
                      onClick={() => void transitionInstallation("revoke")}
                    >
                      Revoke
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
                      Logical uninstall
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <label className="governance-reason">
        Governance reason
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
  return <span className={`state-badge ${state.toLowerCase()}`}>{state}</span>;
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
        label="Lock digest"
        value={installation.immutableFacts.lockDigest}
      />
      <div className="lock-nodes">
        {installation.immutableFacts.dependencyLock.nodes.map((node) => (
          <span key={`${node.packageId}-${node.packageVersion}`}>
            {node.packageId}@{node.packageVersion}
          </span>
        ))}
      </div>
      <small>
        authorizationEffect=NONE · runtimeStateCreated=false ·
        semanticRuntimeReady=false
      </small>
    </div>
  );
}

function shortDigest(value: string): string {
  return value.length > 24 ? `${value.slice(0, 16)}…${value.slice(-8)}` : value;
}
