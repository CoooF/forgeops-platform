import { useState } from "react";

import {
  api,
  describeApiError,
  type DomainInstallation,
  type DomainLockDiff,
  type ProjectDomainLock,
} from "./project-api";

type Run = (operation: () => Promise<void>, success: string) => Promise<void>;

export function ProjectDomainLockPanel({
  actor,
  projectId,
  projectActive,
  locks,
  installations,
  canManage,
  pending,
  run,
  reload,
}: {
  actor: string;
  projectId: string;
  projectActive: boolean;
  locks: ProjectDomainLock[];
  installations: DomainInstallation[];
  canManage: boolean;
  pending: boolean;
  run: Run;
  reload: () => Promise<void>;
}) {
  const current = locks.find((item) => item.lockState.status === "CURRENT");
  const [installationId, setInstallationId] = useState("");
  const [purpose, setPurpose] = useState("Synthetic project domain selection");
  const [diff, setDiff] = useState<DomainLockDiff | null>(null);
  const [diffError, setDiffError] = useState("");

  async function selectInstallation(nextId: string) {
    setInstallationId(nextId);
    setDiff(null);
    setDiffError("");
    if (!nextId || !current || current.immutableFacts.installationId === nextId)
      return;
    try {
      setDiff(
        await api.compareDomainInstallations(
          actor,
          current.immutableFacts.installationId,
          nextId,
        ),
      );
    } catch (error) {
      setDiffError(describeApiError(error));
    }
  }

  return (
    <div className="detail-body domain-lock-panel">
      <div className="section-heading">
        <div>
          <h3>Project DomainLock</h3>
          <p>
            One immutable current dependency graph. Switching creates a new lock
            and preserves the old lock as SUPERSEDED.
          </p>
        </div>
        <span className="truth-chip">semanticRuntimeReady=false</span>
      </div>

      {current ? (
        <section className="current-lock" data-testid="current-domain-lock">
          <div className="title-line">
            <h4>Current · {current.immutableFacts.rootPackageId}</h4>
            <StateBadge state={current.derivedHealth.health} />
          </div>
          <p>
            {current.immutableFacts.rootPackageVersion} · created by{" "}
            {current.immutableFacts.createdBy}
          </p>
          <Digest value={current.immutableFacts.lockDigest} />
          {current.derivedHealth.reasons.length > 0 && (
            <div className="impact-warning">
              {current.derivedHealth.reasons.join(" · ")}
            </div>
          )}
          <div className="lock-nodes">
            {current.immutableFacts.packageVersionRefs.map((item) => (
              <span key={item.packageVersionId}>
                {item.packageId}@{item.packageVersion}
              </span>
            ))}
          </div>
          <small>
            authorizationEffect=NONE · runtimeBindingCreated=false ·
            semanticRuntimeReady=false
          </small>
        </section>
      ) : (
        <div className="empty-state">No current Project DomainLock.</div>
      )}

      {canManage ? (
        <section className="lock-switcher">
          <div className="section-heading">
            <div>
              <h4>
                {current ? "Switch immutable lock" : "Create current lock"}
              </h4>
              <p>
                Only same-organization, healthy INSTALLED_DISABLED records are
                accepted.
              </p>
            </div>
          </div>
          <label>
            Organization installation
            <select
              aria-label="Project DomainLock installation"
              value={installationId}
              onChange={(event) => void selectInstallation(event.target.value)}
            >
              <option value="">Select installation</option>
              {installations.map((item) => (
                <option key={item.installationId} value={item.installationId}>
                  {item.immutableFacts.rootPackageId}@
                  {item.immutableFacts.rootPackageVersion} ·{" "}
                  {item.installationState.state} ·{item.derivedHealth.health}
                </option>
              ))}
            </select>
          </label>
          <label>
            Selection purpose
            <input
              value={purpose}
              onChange={(event) => {
                setPurpose(event.target.value);
              }}
            />
          </label>
          {diffError && (
            <div className="message error-message">{diffError}</div>
          )}
          {diff && <DiffSummary diff={diff} />}
          {!projectActive && (
            <p className="impact-warning">
              Project must be ACTIVE before a new lock is created.
            </p>
          )}
          <button
            disabled={!installationId || !projectActive || pending}
            onClick={() =>
              void run(async () => {
                await api.createProjectDomainLock(
                  actor,
                  projectId,
                  installationId,
                  purpose,
                );
                setInstallationId("");
                setDiff(null);
                await reload();
              }, "Current Project DomainLock persisted; prior current lock remains in history.")
            }
          >
            {current ? "Confirm lock switch" : "Create current lock"}
          </button>
        </section>
      ) : (
        <p className="read-only-note">
          Read-only DomainLock summary; no Manifest private fields shown.
        </p>
      )}

      <section>
        <div className="section-heading">
          <div>
            <h4>Immutable lock history</h4>
            <p>
              Historical digests remain readable after switches and withdrawal
              impact.
            </p>
          </div>
        </div>
        <div className="record-list">
          {locks.map((item) => (
            <article
              key={item.projectDomainLockId}
              className="record-row lock-history-row"
            >
              <div>
                <strong>
                  {item.immutableFacts.rootPackageId}@
                  {item.immutableFacts.rootPackageVersion}
                </strong>
                <small>{shortDigest(item.immutableFacts.lockDigest)}</small>
              </div>
              <StateBadge state={item.lockState.status} />
              <StateBadge state={item.derivedHealth.health} />
              <span>{item.immutableFacts.purpose}</span>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function DiffSummary({ diff }: { diff: DomainLockDiff }) {
  return (
    <div className="diff-summary" data-testid="domain-lock-diff">
      <strong>
        Selection diff · semanticDifferenceStatus=
        {diff.semanticDifferenceStatus}
      </strong>
      <span>{diff.added.length} added</span>
      <span>{diff.removed.length} removed</span>
      <span>{diff.changed.length} changed</span>
      <small>
        Permissions +{diff.permissionsAdded.length}/-
        {diff.permissionsRemoved.length} · trust or visibility changes{" "}
        {diff.visibilityTrustChanges.length}
      </small>
      <pre>{JSON.stringify(diff.budgetDelta, null, 2)}</pre>
    </div>
  );
}

function Digest({ value }: { value: string }) {
  return <code className="lock-digest">{value}</code>;
}

function StateBadge({ state }: { state: string }) {
  return <span className={`state-badge ${state.toLowerCase()}`}>{state}</span>;
}

function shortDigest(value: string): string {
  return value.length > 24 ? `${value.slice(0, 16)}…${value.slice(-8)}` : value;
}
