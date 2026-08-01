import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type SyntheticEvent,
} from "react";

import {
  api,
  describeApiError,
  loadSession,
  LOCAL_ACTORS,
  type AuditEvent,
  type BindableInstallation,
  type DomainInstallation,
  type Me,
  type Membership,
  type Organization,
  type Project,
  type ProjectBinding,
  type ProjectDomainLock,
  type Workspace,
} from "./project-api";
import { DomainRegistry } from "./DomainRegistry";
import { ProjectContextPanel } from "./ProjectContext";
import { ProjectDomainLockPanel } from "./ProjectDomainLock";
import { SemanticKnowledge } from "./SemanticKnowledge";
import type { PlatformStatus } from "./status";
import "./styles.css";

type Tab =
  "overview" | "members" | "packages" | "domain-lock" | "context" | "audit";
type Surface = "projects" | "registry" | "semantic";
type LoadState = "loading" | "ready" | "error";

interface ProjectContext {
  permissions: string[];
  members: Membership[];
  bindings: ProjectBinding[];
  bindable: BindableInstallation[];
  domainInstallations: DomainInstallation[];
  domainLocks: ProjectDomainLock[];
  audit: AuditEvent[];
}

const EMPTY_CONTEXT: ProjectContext = {
  permissions: [],
  members: [],
  bindings: [],
  bindable: [],
  domainInstallations: [],
  domainLocks: [],
  audit: [],
};

const TAB_LABELS: Record<Tab, string> = {
  overview: "项目概览",
  members: "成员权限",
  packages: "场景包",
  "domain-lock": "领域锁",
  context: "上下文",
  audit: "审计记录",
};

export function App() {
  const [actor, setActor] = useState("local-owner");
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [status, setStatus] = useState<PlatformStatus | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [projectContext, setProjectContext] =
    useState<ProjectContext>(EMPTY_CONTEXT);
  const [tab, setTab] = useState<Tab>("overview");
  const [surface, setSurface] = useState<Surface>("projects");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const organization = organizations.find(
    (item) => item.organizationId === organizationId,
  );
  const workspace = workspaces.find((item) => item.workspaceId === workspaceId);
  const project = projects.find((item) => item.projectId === projectId);
  const can = useCallback(
    (permission: string) => projectContext.permissions.includes(permission),
    [projectContext.permissions],
  );

  const visibleProjects = useMemo(() => {
    const term = search.trim().toLowerCase();
    return projects.filter(
      (item) =>
        (statusFilter === "ALL" || item.state === statusFilter) &&
        (!term ||
          `${item.name} ${item.slug} ${item.description}`
            .toLowerCase()
            .includes(term)),
    );
  }, [projects, search, statusFilter]);

  const run = useCallback(
    async (operation: () => Promise<void>, success: string) => {
      setPending(true);
      setError("");
      setNotice("");
      try {
        await operation();
        setNotice(success);
      } catch (operationError) {
        setError(describeApiError(operationError));
      } finally {
        setPending(false);
      }
    },
    [],
  );

  const loadProjectContext = useCallback(
    async (selectedActor: string, selectedProjectId: string) => {
      if (!selectedProjectId) {
        setProjectContext(EMPTY_CONTEXT);
        return;
      }
      const permissions = await api.projectPermissions(
        selectedActor,
        selectedProjectId,
      );
      const [members, bindings, domainLocks] = await Promise.all([
        api.projectMembers(selectedActor, selectedProjectId),
        api.projectBindings(selectedActor, selectedProjectId),
        permissions.permissions.includes("fds.domain-lock.history.view")
          ? api.projectDomainLocks(selectedActor, selectedProjectId)
          : permissions.permissions.includes("fds.domain-lock.view")
            ? api
                .currentProjectDomainLock(selectedActor, selectedProjectId)
                .then((item) => ({
                  items: item ? [item] : [],
                  total: item ? 1 : 0,
                  limit: 1,
                  offset: 0,
                }))
            : Promise.resolve({ items: [], total: 0, limit: 100, offset: 0 }),
      ]);
      let bindable: BindableInstallation[] = [];
      let domainInstallations: DomainInstallation[] = [];
      if (permissions.permissions.includes("package.bind")) {
        bindable = (
          await api.bindableInstallations(selectedActor, selectedProjectId)
        ).items;
      }
      if (permissions.permissions.includes("fds.domain-lock.manage")) {
        domainInstallations = (
          await api.projectDomainInstallations(selectedActor, selectedProjectId)
        ).items;
      }
      setProjectContext({
        permissions: permissions.permissions,
        members: members.items,
        bindings: bindings.items,
        bindable,
        domainInstallations,
        domainLocks: domainLocks.items,
        audit: [],
      });
    },
    [],
  );

  const loadProjects = useCallback(
    async (selectedActor: string, selectedWorkspaceId: string) => {
      if (!selectedWorkspaceId) {
        setProjects([]);
        setProjectId("");
        return;
      }
      const response = await api.projects(selectedActor, selectedWorkspaceId);
      setProjects(response.items);
      const nextProject = response.items[0]?.projectId ?? "";
      setProjectId(nextProject);
      await loadProjectContext(selectedActor, nextProject);
    },
    [loadProjectContext],
  );

  const loadWorkspaces = useCallback(
    async (selectedActor: string, selectedOrganizationId: string) => {
      if (!selectedOrganizationId) {
        setWorkspaces([]);
        setWorkspaceId("");
        setProjects([]);
        return;
      }
      const response = await api.workspaces(
        selectedActor,
        selectedOrganizationId,
      );
      setWorkspaces(response.items);
      const nextWorkspace = response.items[0]?.workspaceId ?? "";
      setWorkspaceId(nextWorkspace);
      await loadProjects(selectedActor, nextWorkspace);
    },
    [loadProjects],
  );

  const reloadSession = useCallback(
    async (selectedActor: string, preferredOrganizationId?: string) => {
      setLoadState("loading");
      setError("");
      setNotice("");
      try {
        const session = await loadSession(selectedActor);
        setStatus(session.status);
        setMe(session.me);
        setOrganizations(session.organizations);
        const nextOrganization =
          session.organizations.find(
            (item) => item.organizationId === preferredOrganizationId,
          )?.organizationId ??
          session.organizations[0]?.organizationId ??
          "";
        setOrganizationId(nextOrganization);
        await loadWorkspaces(selectedActor, nextOrganization);
        setLoadState("ready");
      } catch (sessionError) {
        setStatus(null);
        setMe(null);
        setOrganizations([]);
        setWorkspaces([]);
        setProjects([]);
        setProjectContext(EMPTY_CONTEXT);
        setError(describeApiError(sessionError));
        setLoadState("error");
      }
    },
    [loadWorkspaces],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reloadSession(actor);
    }, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [actor, reloadSession]);

  async function selectOrganization(nextId: string) {
    setOrganizationId(nextId);
    setTab("overview");
    setError("");
    try {
      await loadWorkspaces(actor, nextId);
    } catch (loadError) {
      setError(describeApiError(loadError));
    }
  }

  async function selectWorkspace(nextId: string) {
    setWorkspaceId(nextId);
    setTab("overview");
    setError("");
    try {
      await loadProjects(actor, nextId);
    } catch (loadError) {
      setError(describeApiError(loadError));
    }
  }

  async function selectProject(nextId: string) {
    setProjectId(nextId);
    setTab("overview");
    setError("");
    try {
      await loadProjectContext(actor, nextId);
    } catch (loadError) {
      setError(describeApiError(loadError));
    }
  }

  async function refreshCurrentProject() {
    if (!workspaceId) return;
    const response = await api.projects(actor, workspaceId);
    setProjects(response.items);
    if (projectId) await loadProjectContext(actor, projectId);
  }

  async function openTab(nextTab: Tab) {
    setTab(nextTab);
    if (nextTab === "audit" && project && can("audit.read")) {
      try {
        const response = await api.projectAudit(actor, project.projectId);
        setProjectContext((current) => ({ ...current, audit: response.items }));
      } catch (auditError) {
        setError(describeApiError(auditError));
      }
    }
  }

  if (loadState === "loading") {
    return (
      <FullState
        title="正在打开项目中心"
        detail="正在读取组织范围、项目数据与权限策略…"
      />
    );
  }

  if (loadState === "error" || !status || !me) {
    return (
      <FullState
        title="项目中心暂不可用"
        detail={error || "接口未返回符合本地合成数据边界的状态。"}
        action={
          <button onClick={() => void reloadSession(actor)}>重新连接</button>
        }
      />
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark" aria-label="ForgeOps">
          <span>FO</span>
          <div>
            <strong>ForgeOps</strong>
            <small>
              {surface === "projects"
                ? "工业智能体项目中心"
                : surface === "registry"
                  ? "领域资产注册中心"
                  : "语义与知识治理"}
            </small>
          </div>
        </div>
        <nav className="surface-switcher" aria-label="ForgeOps 功能区">
          <button
            aria-label="项目中心"
            className={surface === "projects" ? "active" : ""}
            onClick={() => {
              setSurface("projects");
            }}
          >
            项目中心
          </button>
          <button
            className={surface === "registry" ? "active" : ""}
            onClick={() => {
              setSurface("registry");
            }}
          >
            领域资产
          </button>
          <button
            aria-label="语义与知识"
            className={surface === "semantic" ? "active" : ""}
            onClick={() => {
              setSurface("semantic");
            }}
          >
            语义与知识
          </button>
        </nav>
        <div className="boundary-strip" aria-label="平台安全边界">
          <Boundary label="运行模式" value="决策建议" />
          <Boundary label="数据边界" value="仅合成数据" />
          <Boundary label="身份来源" value="本地演示" warning />
          <Boundary label="企业系统" value="暂未接入" warning />
        </div>
      </header>

      <aside className="context-rail">
        <section>
          <p className="section-label">当前身份</p>
          <label>
            演示角色
            <select
              aria-label="演示角色"
              value={actor}
              onChange={(event) => {
                setActor(event.target.value);
              }}
            >
              {LOCAL_ACTORS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <p className="identity-caption">
            {actorDisplayName(actor)} · {stateLabel(me.principal.state)}
          </p>
          <p className="local-warning">
            本地工程身份只用于验证权限差异，切换角色不会绕过后端授权。
          </p>
        </section>

        <section className="scope-controls">
          <p className="section-label">工作范围</p>
          <label>
            组织
            <select
              aria-label="组织"
              value={organizationId}
              onChange={(event) => void selectOrganization(event.target.value)}
              disabled={organizations.length === 0}
            >
              {organizations.length === 0 && (
                <option value="">尚未创建组织</option>
              )}
              {organizations.map((item) => (
                <option key={item.organizationId} value={item.organizationId}>
                  {item.name} · {stateLabel(item.state)}
                </option>
              ))}
            </select>
          </label>
          <label>
            工作空间
            <select
              aria-label="工作空间"
              value={workspaceId}
              onChange={(event) => void selectWorkspace(event.target.value)}
              disabled={workspaces.length === 0}
            >
              {workspaces.length === 0 && (
                <option value="">尚未创建工作空间</option>
              )}
              {workspaces.map((item) => (
                <option key={item.workspaceId} value={item.workspaceId}>
                  {item.name} · {stateLabel(item.state)}
                </option>
              ))}
            </select>
          </label>
        </section>

        <div className="rail-fact">
          <span>动作安全边界</span>
          <strong>
            {status.actionAdapter === "MOCK" ? "仅模拟" : status.actionAdapter}
          </strong>
          <small>不修改正式排程，不控制外部设备</small>
        </div>
      </aside>

      {surface === "registry" ? (
        <DomainRegistry
          actor={actor}
          organizationId={organizationId}
          canRegisterPublic={hasPublicRegistryManager(me)}
          canManageOrganization={
            organization?.state === "ACTIVE" &&
            hasOrganizationAdmin(me, organizationId)
          }
          pending={pending}
          run={run}
          notice={notice}
          error={error}
        />
      ) : surface === "semantic" ? (
        <SemanticKnowledge
          actor={actor}
          organizationId={organizationId}
          canManage={
            hasPublicRegistryManager(me) ||
            hasOrganizationAdmin(me, organizationId)
          }
        />
      ) : (
        <main className="workspace">
          <div className="workspace-heading">
            <div>
              <p className="section-label">
                {organization?.name ?? "本地合成环境"}
              </p>
              <h1>{workspace?.name ?? "建立第一个工业智能体项目空间"}</h1>
              <p>
                {workspace
                  ? "在同一项目范围内管理成员权限、领域包、固定版本和审计证据。"
                  : "从组织和工作空间开始，逐步装配领域能力、工作流与智能体。"}
              </p>
            </div>
            <div className="scope-actions">
              {hasPlatformOwner(me) && (
                <CreateOrganization
                  actor={actor}
                  run={run}
                  reload={(createdOrganizationId) =>
                    reloadSession(actor, createdOrganizationId)
                  }
                />
              )}
              {organization?.state === "ACTIVE" &&
                hasOrganizationAdmin(me, organizationId) && (
                  <CreateWorkspace
                    actor={actor}
                    organizationId={organizationId}
                    run={run}
                    reload={() => loadWorkspaces(actor, organizationId)}
                  />
                )}
              {workspace?.state === "ACTIVE" &&
                hasProjectCreator(me, organizationId, workspaceId) && (
                  <CreateProject
                    actor={actor}
                    workspaceId={workspaceId}
                    run={run}
                    reload={() => loadProjects(actor, workspaceId)}
                  />
                )}
            </div>
          </div>

          <section className="capability-strip" aria-label="平台建设进度">
            <CapabilityStep
              index="01"
              title="组织与项目"
              status="已可用"
              active
            />
            <CapabilityStep
              index="02"
              title="领域资产"
              status="已可用"
              active
            />
            <CapabilityStep
              index="03"
              title="语义与知识"
              status="已可用"
              active
            />
            <CapabilityStep
              index="04"
              title="工作流与智能体"
              status="后续建设"
            />
          </section>

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

          <section className="project-layout">
            <div className="project-index">
              <div className="index-tools">
                <input
                  aria-label="搜索项目"
                  placeholder="搜索项目名称或标识"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                  }}
                />
                <select
                  aria-label="筛选项目状态"
                  value={statusFilter}
                  onChange={(event) => {
                    setStatusFilter(event.target.value);
                  }}
                >
                  <option value="ALL">全部状态</option>
                  <option value="DRAFT">草稿</option>
                  <option value="ACTIVE">运行中</option>
                  <option value="ARCHIVED">已归档</option>
                </select>
              </div>
              <div className="project-count">
                <span>当前项目</span>
                <strong>
                  {visibleProjects.length.toString().padStart(2, "0")}
                </strong>
              </div>
              <nav aria-label="项目列表">
                {visibleProjects.length === 0 ? (
                  <EmptyState text="当前范围还没有项目。请先在上方创建组织、工作空间和项目。" />
                ) : (
                  visibleProjects.map((item) => (
                    <button
                      className={
                        item.projectId === projectId
                          ? "project-row selected"
                          : "project-row"
                      }
                      key={item.projectId}
                      onClick={() => void selectProject(item.projectId)}
                    >
                      <span
                        className={`state-dot ${item.state.toLowerCase()}`}
                      />
                      <span>
                        <strong>{item.name}</strong>
                        <small>{item.slug}</small>
                      </span>
                      <code>{stateLabel(item.state)}</code>
                    </button>
                  ))
                )}
              </nav>
            </div>

            <div className="project-detail">
              {!project ? (
                <div className="project-welcome">
                  <span className="welcome-index">FORGEOPS / 项目</span>
                  <h2>从一个受治理的项目开始</h2>
                  <p>
                    项目是工作流、智能体、数据权限和领域知识的共同边界。创建后可继续绑定领域资产与固定版本。
                  </p>
                  <div className="welcome-flow" aria-label="项目搭建流程">
                    <span>组织</span>
                    <i />
                    <span>工作空间</span>
                    <i />
                    <span>项目</span>
                    <i />
                    <span>领域能力</span>
                  </div>
                </div>
              ) : (
                <>
                  <div className="detail-heading">
                    <div>
                      <div className="title-line">
                        <h2>{project.name}</h2>
                        <StateBadge state={project.state} />
                      </div>
                      <code>{project.projectId}</code>
                    </div>
                    <span className="version-chip">v{project.version}</span>
                  </div>
                  <nav className="tabs" aria-label="项目详情视图">
                    {(
                      [
                        "overview",
                        "members",
                        "packages",
                        "domain-lock",
                        "context",
                        "audit",
                      ] as const
                    ).map((item) => (
                      <button
                        key={item}
                        className={tab === item ? "active" : ""}
                        onClick={() => void openTab(item)}
                      >
                        {TAB_LABELS[item]}
                      </button>
                    ))}
                  </nav>

                  {tab === "overview" && (
                    <Overview
                      project={project}
                      can={can}
                      actor={actor}
                      pending={pending}
                      run={run}
                      reload={refreshCurrentProject}
                    />
                  )}
                  {tab === "members" && (
                    <Members
                      members={projectContext.members}
                      canManage={
                        can("membership.manage") && project.state !== "ARCHIVED"
                      }
                      actor={actor}
                      organizationId={organizationId}
                      projectId={project.projectId}
                      pending={pending}
                      run={run}
                      reload={() =>
                        loadProjectContext(actor, project.projectId)
                      }
                    />
                  )}
                  {tab === "packages" && (
                    <Packages
                      bindings={projectContext.bindings}
                      bindable={projectContext.bindable}
                      canBind={
                        can("package.bind") && project.state !== "ARCHIVED"
                      }
                      actor={actor}
                      projectId={project.projectId}
                      pending={pending}
                      run={run}
                      reload={() =>
                        loadProjectContext(actor, project.projectId)
                      }
                    />
                  )}
                  {tab === "domain-lock" && (
                    <ProjectDomainLockPanel
                      actor={actor}
                      projectId={project.projectId}
                      projectActive={project.state === "ACTIVE"}
                      locks={projectContext.domainLocks}
                      installations={projectContext.domainInstallations}
                      canManage={
                        can("fds.domain-lock.manage") &&
                        project.state !== "ARCHIVED"
                      }
                      pending={pending}
                      run={run}
                      reload={() =>
                        loadProjectContext(actor, project.projectId)
                      }
                    />
                  )}
                  {tab === "context" && (
                    <ProjectContextPanel
                      actor={actor}
                      projectId={project.projectId}
                      currentLock={
                        projectContext.domainLocks.find(
                          (item) => item.lockState.status === "CURRENT",
                        ) ?? null
                      }
                      canQuery={can("semantic.query")}
                      canCompile={can("context.compile")}
                      canValidate={can("grounding.validate")}
                    />
                  )}
                  {tab === "audit" && (
                    <Audit
                      events={projectContext.audit}
                      allowed={can("audit.read")}
                    />
                  )}
                </>
              )}
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

function Overview({
  project,
  can,
  actor,
  pending,
  run,
  reload,
}: {
  project: Project;
  can: (permission: string) => boolean;
  actor: string;
  pending: boolean;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: () => Promise<void>;
}) {
  return (
    <div className="detail-body">
      <dl className="facts-grid">
        <div>
          <dt>项目说明</dt>
          <dd>{project.description || "暂未填写项目说明。"}</dd>
        </div>
        <div>
          <dt>项目标识</dt>
          <dd>{project.slug}</dd>
        </div>
        <div>
          <dt>创建时间</dt>
          <dd>{formatTime(project.createdAt)}</dd>
        </div>
        <div>
          <dt>更新时间</dt>
          <dd>{formatTime(project.updatedAt)}</dd>
        </div>
      </dl>
      <div className="action-bar">
        {can("project.update") && project.state !== "ARCHIVED" && (
          <EditProject
            project={project}
            actor={actor}
            run={run}
            reload={reload}
          />
        )}
        {can("project.activate") && project.state === "DRAFT" && (
          <button
            disabled={pending}
            onClick={() =>
              void run(async () => {
                await api.transitionProject(actor, project, "activate");
                await reload();
              }, "项目已激活，状态已写入数据库。")
            }
          >
            激活项目
          </button>
        )}
        {can("project.archive") && project.state !== "ARCHIVED" && (
          <button
            className="danger-button"
            disabled={pending}
            onClick={() =>
              void run(async () => {
                await api.transitionProject(actor, project, "archive");
                await reload();
              }, "项目已归档，历史记录仍可查询。")
            }
          >
            归档项目
          </button>
        )}
        {!can("project.update") && (
          <p className="read-only-note">当前身份仅可查看此项目。</p>
        )}
      </div>
    </div>
  );
}

function Members({
  members,
  canManage,
  actor,
  organizationId,
  projectId,
  pending,
  run,
  reload,
}: {
  members: Membership[];
  canManage: boolean;
  actor: string;
  organizationId: string;
  projectId: string;
  pending: boolean;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: () => Promise<void>;
}) {
  return (
    <div className="detail-body">
      <div className="section-heading">
        <div>
          <h3>项目成员与有效权限</h3>
          <p>组织、工作空间和项目级授权分别记录，并由后端实时计算有效范围。</p>
        </div>
        {canManage && (
          <AddMember
            actor={actor}
            organizationId={organizationId}
            projectId={projectId}
            run={run}
            reload={reload}
          />
        )}
      </div>
      {members.length === 0 ? (
        <EmptyState text="当前项目范围内没有可见的成员授权。" />
      ) : (
        <div className="record-list">
          {members.map((membership) => (
            <article key={membership.membershipId} className="record-row">
              <div>
                <strong>
                  {membership.principal?.displayName ?? membership.principalId}
                </strong>
                <small>
                  {membership.principal?.subjectRef} ·{" "}
                  {scopeTypeLabel(membership.scopeType)}
                </small>
              </div>
              <code>{roleLabel(membership.role)}</code>
              <StateBadge state={membership.state} />
              {canManage &&
              membership.state === "ACTIVE" &&
              membership.scopeType === "PROJECT" ? (
                <div className="row-actions">
                  <button
                    className="quiet-button"
                    disabled={pending}
                    onClick={() =>
                      void run(async () => {
                        await api.transitionMembership(
                          actor,
                          membership,
                          "suspend",
                        );
                        await reload();
                      }, "成员权限已暂停，后续请求将立即失去访问能力。")
                    }
                  >
                    暂停
                  </button>
                  <button
                    className="quiet-button"
                    disabled={pending}
                    onClick={() =>
                      void run(async () => {
                        await api.transitionMembership(
                          actor,
                          membership,
                          "revoke",
                        );
                        await reload();
                      }, "成员权限已撤销，历史授权记录继续保留。")
                    }
                  >
                    撤销
                  </button>
                </div>
              ) : (
                <span />
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function Packages({
  bindings,
  bindable,
  canBind,
  actor,
  projectId,
  pending,
  run,
  reload,
}: {
  bindings: ProjectBinding[];
  bindable: BindableInstallation[];
  canBind: boolean;
  actor: string;
  projectId: string;
  pending: boolean;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: () => Promise<void>;
}) {
  return (
    <div className="detail-body split-sections">
      <section>
        <div className="section-heading">
          <div>
            <h3>项目场景包绑定</h3>
            <p>
              绑定只固定一个安装版本，不代表已发布，也不会自动获得运行权限。
            </p>
          </div>
        </div>
        {bindings.length === 0 ? (
          <EmptyState text="当前项目还没有绑定场景包。" />
        ) : (
          <div className="record-list">
            {bindings.map((binding) => (
              <article
                key={binding.bindingId}
                className="record-row package-row"
              >
                <div>
                  <strong>{binding.packageId}</strong>
                  <small>
                    {binding.packageVersion} · 安装记录{" "}
                    {shortId(binding.installationId)}
                  </small>
                </div>
                <code>{binding.packageKind}</code>
                <StateBadge state={binding.state} />
                {canBind && binding.state === "ACTIVE" ? (
                  <button
                    className="quiet-button"
                    disabled={pending}
                    onClick={() =>
                      void run(async () => {
                        await api.disableBinding(actor, binding);
                        await reload();
                      }, "场景包绑定已停用，历史记录继续保留。")
                    }
                  >
                    停用
                  </button>
                ) : (
                  <span />
                )}
              </article>
            ))}
          </div>
        )}
      </section>
      {canBind && (
        <section>
          <div className="section-heading">
            <div>
              <h3>可绑定的安装版本</h3>
              <p>这里只显示通过状态与权限校验的本地场景包安装记录。</p>
            </div>
          </div>
          {bindable.length === 0 ? (
            <EmptyState text="目前没有符合绑定条件的场景包安装版本。" />
          ) : (
            <div className="record-list">
              {bindable.map((installation) => (
                <article
                  key={installation.installationId}
                  className="record-row package-row"
                >
                  <div>
                    <strong>{installation.packageId}</strong>
                    <small>{installation.packageVersion}</small>
                  </div>
                  <code>{installation.state}</code>
                  <span />
                  <button
                    disabled={pending || installation.alreadyBound}
                    onClick={() =>
                      void run(async () => {
                        await api.bindPackage(
                          actor,
                          projectId,
                          installation.installationId,
                        );
                        await reload();
                      }, "场景包安装版本已绑定到当前项目。")
                    }
                  >
                    {installation.alreadyBound ? "已绑定" : "绑定"}
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function Audit({
  events,
  allowed,
}: {
  events: AuditEvent[];
  allowed: boolean;
}) {
  if (!allowed)
    return <ForbiddenState text="当前身份没有读取项目审计记录的权限。" />;
  if (events.length === 0)
    return <EmptyState text="当前项目还没有可见的审计事件。" />;
  return (
    <div className="detail-body audit-list">
      {events.map((event) => (
        <article key={event.eventId}>
          <time>{formatTime(event.occurredAt)}</time>
          <div>
            <strong>{event.eventType}</strong>
            <small>
              {event.actorRef} · {event.reasonCode} · trace 链路{" "}
              {shortId(event.traceId)}
            </small>
          </div>
          <StateBadge state={event.result} />
        </article>
      ))}
    </div>
  );
}

function CreateOrganization({
  actor,
  run,
  reload,
}: {
  actor: string;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: (organizationId: string) => Promise<void>;
}) {
  return (
    <CompactForm
      label="创建组织"
      fields={["name", "slug"]}
      submit={async (values) => {
        await run(async () => {
          const created = await api.createOrganization(actor, {
            name: values.name ?? "",
            slug: values.slug ?? "",
          });
          await reload(created.organizationId);
        }, "组织已创建，并为当前身份建立负责人权限。 ");
      }}
    />
  );
}

function CreateWorkspace({
  actor,
  organizationId,
  run,
  reload,
}: {
  actor: string;
  organizationId: string;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: () => Promise<void>;
}) {
  return (
    <CompactForm
      label="新建工作空间"
      fields={["name", "slug"]}
      submit={async (values) => {
        await run(async () => {
          await api.createWorkspace(actor, organizationId, {
            name: values.name ?? "",
            slug: values.slug ?? "",
          });
          await reload();
        }, "工作空间已创建到当前组织。 ");
      }}
    />
  );
}

function CreateProject({
  actor,
  workspaceId,
  run,
  reload,
}: {
  actor: string;
  workspaceId: string;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: () => Promise<void>;
}) {
  return (
    <CompactForm
      label="新建项目"
      fields={["name", "slug", "description"]}
      submit={async (values) => {
        await run(async () => {
          await api.createProject(actor, workspaceId, {
            name: values.name ?? "",
            slug: values.slug ?? "",
            description: values.description ?? "",
          });
          await reload();
        }, "项目草稿已创建并写入数据库。 ");
      }}
    />
  );
}

function EditProject({
  project,
  actor,
  run,
  reload,
}: {
  project: Project;
  actor: string;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: () => Promise<void>;
}) {
  return (
    <CompactForm
      label="编辑项目"
      fields={["name", "slug", "description"]}
      initial={{
        name: project.name,
        slug: project.slug,
        description: project.description,
      }}
      submit={async (values) => {
        await run(async () => {
          await api.updateProject(actor, project, {
            name: values.name ?? "",
            slug: values.slug ?? "",
            description: values.description ?? "",
          });
          await reload();
        }, "项目已更新，并通过乐观并发控制校验。 ");
      }}
    />
  );
}

function AddMember({
  actor,
  organizationId,
  projectId,
  run,
  reload,
}: {
  actor: string;
  organizationId: string;
  projectId: string;
  run: (operation: () => Promise<void>, success: string) => Promise<void>;
  reload: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [principalRef, setPrincipalRef] = useState("local-viewer");
  const [role, setRole] = useState("PROJECT_VIEWER");
  return (
    <div className="inline-form-wrap">
      <button
        onClick={() => {
          setOpen((value) => !value);
        }}
      >
        添加成员
      </button>
      {open && (
        <form
          className="popover-form"
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              await api.createProjectMembership(
                actor,
                organizationId,
                projectId,
                principalRef,
                role,
              );
              await reload();
              setOpen(false);
            }, "项目成员权限已通过后端角色策略创建。 ");
          }}
        >
          <label>
            成员身份
            <select
              value={principalRef}
              onChange={(event) => {
                setPrincipalRef(event.target.value);
              }}
            >
              {LOCAL_ACTORS.filter((item) => item.value !== "local-owner").map(
                (item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ),
              )}
            </select>
          </label>
          <label>
            项目角色
            <select
              value={role}
              onChange={(event) => {
                setRole(event.target.value);
              }}
            >
              <option value="PROJECT_OWNER">项目负责人</option>
              <option value="PROJECT_EDITOR">项目编辑者</option>
              <option value="PROJECT_VIEWER">只读查看者</option>
              <option value="PACKAGE_OPERATOR">能力包管理员</option>
              <option value="AUDITOR">审计员</option>
            </select>
          </label>
          <button type="submit">确认授权</button>
        </form>
      )}
    </div>
  );
}

function CompactForm({
  label,
  fields,
  initial = {},
  submit,
}: {
  label: string;
  fields: ("name" | "slug" | "description")[];
  initial?: Record<string, string>;
  submit: (values: Record<string, string>) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string>>(initial);
  function onSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit(values).then(() => {
      setOpen(false);
    });
  }
  return (
    <div className="inline-form-wrap">
      <button
        onClick={() => {
          setOpen((value) => !value);
        }}
      >
        {label}
      </button>
      {open && (
        <form className="popover-form" onSubmit={onSubmit}>
          {fields.map((field) => (
            <label key={field}>
              {fieldLabel(field)}
              {field === "description" ? (
                <textarea
                  value={values[field] ?? ""}
                  onChange={(event) => {
                    setValues({ ...values, [field]: event.target.value });
                  }}
                />
              ) : (
                <input
                  required
                  value={values[field] ?? ""}
                  onChange={(event) => {
                    setValues({ ...values, [field]: event.target.value });
                  }}
                />
              )}
            </label>
          ))}
          <button type="submit">保存</button>
        </form>
      )}
    </div>
  );
}

function Boundary({
  label,
  value,
  warning = false,
}: {
  label: string;
  value: string;
  warning?: boolean;
}) {
  return (
    <div className={warning ? "boundary-item warning" : "boundary-item"}>
      <span>{label}</span>
      <strong>{value}</strong>
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

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function ForbiddenState({ text }: { text: string }) {
  return (
    <div className="forbidden-state">
      <strong>当前范围受限</strong>
      <p>{text}</p>
    </div>
  );
}

function FullState({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: React.ReactNode;
}) {
  return (
    <main className="full-state">
      <p className="section-label">FORGEOPS / 本地合成环境</p>
      <h1>{title}</h1>
      <p>{detail}</p>
      {action}
    </main>
  );
}

function CapabilityStep({
  index,
  title,
  status,
  active = false,
}: {
  index: string;
  title: string;
  status: string;
  active?: boolean;
}) {
  return (
    <div className={active ? "capability-step active" : "capability-step"}>
      <span>{index}</span>
      <strong>{title}</strong>
      <small>{status}</small>
    </div>
  );
}

function actorDisplayName(actor: string): string {
  return LOCAL_ACTORS.find((item) => item.value === actor)?.label ?? actor;
}

function fieldLabel(field: "name" | "slug" | "description"): string {
  return {
    name: "名称",
    slug: "唯一标识",
    description: "说明",
  }[field];
}

function scopeTypeLabel(scopeType: string): string {
  return (
    {
      PLATFORM: "平台级",
      ORGANIZATION: "组织级",
      WORKSPACE: "工作空间级",
      PROJECT: "项目级",
    }[scopeType] ?? scopeType
  );
}

function roleLabel(role: string): string {
  return (
    {
      ORG_OWNER: "组织负责人",
      ORG_ADMIN: "组织管理员",
      WORKSPACE_ADMIN: "工作空间管理员",
      PROJECT_OWNER: "项目负责人",
      PROJECT_EDITOR: "项目编辑者",
      PROJECT_VIEWER: "只读查看者",
      PACKAGE_OPERATOR: "能力包管理员",
      AUDITOR: "审计员",
    }[role] ?? role
  );
}

function stateLabel(state: string): string {
  return (
    {
      ACTIVE: "运行中",
      DISABLED: "已停用",
      DRAFT: "草稿",
      ARCHIVED: "已归档",
      SUSPENDED: "已暂停",
      REVOKED: "已撤销",
      SUCCESS: "成功",
      DENIED: "已拒绝",
      CURRENT: "当前版本",
      SUPERSEDED: "历史版本",
      HEALTHY_FOR_SELECTION: "状态正常",
      AT_RISK: "存在风险",
      BLOCKED_FOR_NEW_USE: "禁止新使用",
      REGISTERED_VALIDATED: "已登记校验",
      QUARANTINED: "已隔离",
      WITHDRAWN: "已撤回",
      INSTALLED_DISABLED: "已安装未启用",
      LOGICALLY_UNINSTALLED: "已逻辑卸载",
    }[state] ?? state
  );
}

function hasPlatformOwner(me: Me): boolean {
  return me.memberships.some(
    (membership) =>
      membership.state === "ACTIVE" &&
      membership.scopeType === "PLATFORM" &&
      membership.role === "ORG_OWNER",
  );
}

function hasPublicRegistryManager(me: Me): boolean {
  return me.memberships.some(
    (membership) =>
      membership.state === "ACTIVE" &&
      membership.scopeType === "PLATFORM" &&
      ["ORG_OWNER", "PACKAGE_OPERATOR"].includes(membership.role),
  );
}

function hasOrganizationAdmin(me: Me, organizationId: string): boolean {
  return me.memberships.some(
    (membership) =>
      membership.state === "ACTIVE" &&
      ((membership.scopeType === "PLATFORM" &&
        membership.role === "ORG_OWNER") ||
        (membership.scopeType === "ORGANIZATION" &&
          membership.scopeId === organizationId &&
          ["ORG_OWNER", "ORG_ADMIN"].includes(membership.role))),
  );
}

function hasProjectCreator(
  me: Me,
  organizationId: string,
  workspaceId: string,
): boolean {
  return me.memberships.some(
    (membership) =>
      membership.state === "ACTIVE" &&
      ((membership.scopeType === "PLATFORM" &&
        membership.role === "ORG_OWNER") ||
        (membership.scopeType === "ORGANIZATION" &&
          membership.scopeId === organizationId &&
          ["ORG_OWNER", "ORG_ADMIN"].includes(membership.role)) ||
        (membership.scopeType === "WORKSPACE" &&
          membership.scopeId === workspaceId &&
          membership.role === "WORKSPACE_ADMIN")),
  );
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}
