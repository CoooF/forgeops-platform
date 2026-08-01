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
  const [purpose, setPurpose] = useState("本地合成项目领域版本选择");
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
          <h3>项目领域锁</h3>
          <p>
            项目始终固定一份不可变依赖图；切换版本会创建新锁，旧锁作为历史版本保留。
          </p>
        </div>
        <span className="truth-chip">语义运行时尚未启用</span>
      </div>

      {current ? (
        <section className="current-lock" data-testid="current-domain-lock">
          <div className="title-line">
            <h4>当前版本 · {current.immutableFacts.rootPackageId}</h4>
            <StateBadge state={current.derivedHealth.health} />
          </div>
          <p>
            {current.immutableFacts.rootPackageVersion} · 创建人{" "}
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
          <small>不产生授权 · 未创建运行绑定 · 语义运行时尚未启用</small>
        </section>
      ) : (
        <div className="empty-state">当前项目还没有固定领域版本。</div>
      )}

      {canManage ? (
        <section className="lock-switcher">
          <div className="section-heading">
            <div>
              <h4>{current ? "切换固定领域版本" : "创建当前领域锁"}</h4>
              <p>只能选择同一组织内状态正常、已安装未启用的领域组合。</p>
            </div>
          </div>
          <label>
            组织安装版本
            <select
              aria-label="项目领域锁安装版本"
              value={installationId}
              onChange={(event) => void selectInstallation(event.target.value)}
            >
              <option value="">选择领域安装记录</option>
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
            选择原因
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
            <p className="impact-warning">项目激活后才能创建或切换领域锁。</p>
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
              }, "当前项目领域锁已写入数据库，原版本已转入不可变历史。")
            }
          >
            {current ? "确认切换版本" : "创建当前领域锁"}
          </button>
        </section>
      ) : (
        <p className="read-only-note">
          当前身份只能查看领域锁摘要，Manifest 私有字段不会展示。
        </p>
      )}

      <section>
        <div className="section-heading">
          <div>
            <h4>不可变版本历史</h4>
            <p>发生切换或撤回影响后，历史摘要仍可读取和调查。</p>
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
        版本差异 · 语义差异状态：
        {semanticDifferenceLabel(diff.semanticDifferenceStatus)}
      </strong>
      <span>新增 {diff.added.length}</span>
      <span>移除 {diff.removed.length}</span>
      <span>变更 {diff.changed.length}</span>
      <small>
        权限 +{diff.permissionsAdded.length}/-{diff.permissionsRemoved.length} ·
        可信或可见范围变化 {diff.visibilityTrustChanges.length}
      </small>
      <pre>{JSON.stringify(diff.budgetDelta, null, 2)}</pre>
    </div>
  );
}

function Digest({ value }: { value: string }) {
  return <code className="lock-digest">{value}</code>;
}

function StateBadge({ state }: { state: string }) {
  return (
    <span className={`state-badge ${state.toLowerCase()}`}>
      {stateLabel(state)}
    </span>
  );
}

function stateLabel(state: string): string {
  return (
    {
      CURRENT: "当前版本",
      SUPERSEDED: "历史版本",
      HEALTHY_FOR_SELECTION: "状态正常",
      AT_RISK: "存在风险",
      BLOCKED_FOR_NEW_USE: "禁止新使用",
      INSTALLED_DISABLED: "已安装未启用",
      DISABLED: "已停用",
      REVOKED: "已撤销",
    }[state] ?? state
  );
}

function semanticDifferenceLabel(state: string): string {
  return (
    {
      NOT_EVALUATED: "尚未评估",
      NO_DIFFERENCE: "无差异",
      DIFFERENT: "存在差异",
    }[state] ?? state
  );
}

function shortDigest(value: string): string {
  return value.length > 24 ? `${value.slice(0, 16)}…${value.slice(-8)}` : value;
}
