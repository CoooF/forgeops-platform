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
  type Me,
  type Membership,
  type Organization,
  type Project,
  type ProjectBinding,
  type Workspace,
} from "./project-api";
import type { PlatformStatus } from "./status";
import "./styles.css";

type Tab = "overview" | "members" | "packages" | "audit";
type LoadState = "loading" | "ready" | "error";

interface ProjectContext {
  permissions: string[];
  members: Membership[];
  bindings: ProjectBinding[];
  bindable: BindableInstallation[];
  audit: AuditEvent[];
}

const EMPTY_CONTEXT: ProjectContext = {
  permissions: [],
  members: [],
  bindings: [],
  bindable: [],
  audit: [],
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
      const [members, bindings] = await Promise.all([
        api.projectMembers(selectedActor, selectedProjectId),
        api.projectBindings(selectedActor, selectedProjectId),
      ]);
      let bindable: BindableInstallation[] = [];
      if (permissions.permissions.includes("package.bind")) {
        bindable = (
          await api.bindableInstallations(selectedActor, selectedProjectId)
        ).items;
      }
      setProjectContext({
        permissions: permissions.permissions,
        members: members.items,
        bindings: bindings.items,
        bindable,
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
    async (selectedActor: string) => {
      setLoadState("loading");
      setError("");
      setNotice("");
      try {
        const session = await loadSession(selectedActor);
        setStatus(session.status);
        setMe(session.me);
        setOrganizations(session.organizations);
        const nextOrganization = session.organizations[0]?.organizationId ?? "";
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
        title="Opening Project Center"
        detail="Reading persisted scope and policy…"
      />
    );
  }

  if (loadState === "error" || !status || !me) {
    return (
      <FullState
        title="Project Center unavailable"
        detail={
          error || "The API did not return a safe local synthetic boundary."
        }
        action={
          <button onClick={() => void reloadSession(actor)}>Retry</button>
        }
      />
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark" aria-label="ForgeOps">
          <span>F/O</span>
          <div>
            <strong>ForgeOps</strong>
            <small>Project Center</small>
          </div>
        </div>
        <div className="boundary-strip" aria-label="platform safety boundary">
          <Boundary label="Mode" value="Advisory only" />
          <Boundary label="Data" value={status.dataMode} />
          <Boundary label="Identity" value={status.identityMode} warning />
          <Boundary label="Enterprise" value="Not connected" warning />
        </div>
      </header>

      <aside className="context-rail">
        <section>
          <p className="section-label">Local identity</p>
          <label>
            Synthetic principal
            <select
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
            {me.principal.displayName} · {me.principal.state}
          </p>
          <p className="local-warning">
            Development adapter only. Selecting a name does not grant a role.
          </p>
        </section>

        <section className="scope-controls">
          <p className="section-label">Scope</p>
          <label>
            Organization
            <select
              value={organizationId}
              onChange={(event) => void selectOrganization(event.target.value)}
              disabled={organizations.length === 0}
            >
              {organizations.length === 0 && (
                <option value="">No visible organizations</option>
              )}
              {organizations.map((item) => (
                <option key={item.organizationId} value={item.organizationId}>
                  {item.name} · {item.state}
                </option>
              ))}
            </select>
          </label>
          <label>
            Workspace
            <select
              value={workspaceId}
              onChange={(event) => void selectWorkspace(event.target.value)}
              disabled={workspaces.length === 0}
            >
              {workspaces.length === 0 && (
                <option value="">No visible workspaces</option>
              )}
              {workspaces.map((item) => (
                <option key={item.workspaceId} value={item.workspaceId}>
                  {item.name} · {item.state}
                </option>
              ))}
            </select>
          </label>
        </section>

        <div className="rail-fact">
          <span>Action adapter</span>
          <strong>{status.actionAdapter}</strong>
          <small>No external execution route</small>
        </div>
      </aside>

      <main className="workspace">
        <div className="workspace-heading">
          <div>
            <p className="section-label">
              {organization?.slug ?? "NO ORGANIZATION"}
            </p>
            <h1>{workspace?.name ?? "Create a governed project scope"}</h1>
            <p>
              Projects isolate memberships, package bindings, lifecycle state,
              and audit evidence.
            </p>
          </div>
          <div className="scope-actions">
            {organizations.length === 0 && hasPlatformOwner(me) && (
              <CreateOrganization
                actor={actor}
                run={run}
                reload={() => reloadSession(actor)}
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
                aria-label="Search projects"
                placeholder="Search projects"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                }}
              />
              <select
                aria-label="Filter project status"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value);
                }}
              >
                <option value="ALL">All states</option>
                <option value="DRAFT">Draft</option>
                <option value="ACTIVE">Active</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>
            <div className="project-count">
              <span>Visible projects</span>
              <strong>
                {visibleProjects.length.toString().padStart(2, "0")}
              </strong>
            </div>
            <nav aria-label="Projects">
              {visibleProjects.length === 0 ? (
                <EmptyState text="No projects match this scope and filter." />
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
                    <span className={`state-dot ${item.state.toLowerCase()}`} />
                    <span>
                      <strong>{item.name}</strong>
                      <small>{item.slug}</small>
                    </span>
                    <code>{item.state}</code>
                  </button>
                ))
              )}
            </nav>
          </div>

          <div className="project-detail">
            {!project ? (
              <EmptyState text="Select or create a project to inspect its governed state." />
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
                <nav className="tabs" aria-label="Project detail views">
                  {(["overview", "members", "packages", "audit"] as const).map(
                    (item) => (
                      <button
                        key={item}
                        className={tab === item ? "active" : ""}
                        onClick={() => void openTab(item)}
                      >
                        {item}
                      </button>
                    ),
                  )}
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
                    reload={() => loadProjectContext(actor, project.projectId)}
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
                    reload={() => loadProjectContext(actor, project.projectId)}
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
          <dt>Description</dt>
          <dd>{project.description || "No description recorded."}</dd>
        </div>
        <div>
          <dt>Slug</dt>
          <dd>{project.slug}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatTime(project.createdAt)}</dd>
        </div>
        <div>
          <dt>Updated</dt>
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
              }, "Project activated from persisted API state.")
            }
          >
            Activate project
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
              }, "Project archived; history remains readable.")
            }
          >
            Archive project
          </button>
        )}
        {!can("project.update") && (
          <p className="read-only-note">Read-only project access.</p>
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
          <h3>Effective scope memberships</h3>
          <p>
            Organization, workspace, and direct project grants are shown
            separately.
          </p>
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
        <EmptyState text="No visible memberships for this project path." />
      ) : (
        <div className="record-list">
          {members.map((membership) => (
            <article key={membership.membershipId} className="record-row">
              <div>
                <strong>
                  {membership.principal?.displayName ?? membership.principalId}
                </strong>
                <small>
                  {membership.principal?.subjectRef} · {membership.scopeType}
                </small>
              </div>
              <code>{membership.role}</code>
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
                      }, "Membership suspended; new requests lose access immediately.")
                    }
                  >
                    Suspend
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
                      }, "Membership revoked; grant history retained.")
                    }
                  >
                    Revoke
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
            <h3>Project bindings</h3>
            <p>
              A binding is a fixed installation reference, not a release or
              permission grant.
            </p>
          </div>
        </div>
        {bindings.length === 0 ? (
          <EmptyState text="No package installation is bound to this project." />
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
                    {binding.packageVersion} · installation{" "}
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
                      }, "Binding disabled; historical record retained.")
                    }
                  >
                    Disable
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
              <h3>Eligible installations</h3>
              <p>
                Only approved, permission-granted local Scenario installations
                appear.
              </p>
            </div>
          </div>
          {bindable.length === 0 ? (
            <EmptyState text="No installation currently passes binding eligibility." />
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
                      }, "Scenario installation bound to the real project ID.")
                    }
                  >
                    {installation.alreadyBound ? "Already bound" : "Bind"}
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
    return (
      <ForbiddenState text="Your current scope does not grant audit.read." />
    );
  if (events.length === 0)
    return <EmptyState text="No project-scoped audit event recorded yet." />;
  return (
    <div className="detail-body audit-list">
      {events.map((event) => (
        <article key={event.eventId}>
          <time>{formatTime(event.occurredAt)}</time>
          <div>
            <strong>{event.eventType}</strong>
            <small>
              {event.actorRef} · {event.reasonCode} · trace{" "}
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
  reload: () => Promise<void>;
}) {
  return (
    <CompactForm
      label="Create organization"
      fields={["name", "slug"]}
      submit={async (values) => {
        await run(async () => {
          await api.createOrganization(actor, {
            name: values.name ?? "",
            slug: values.slug ?? "",
          });
          await reload();
        }, "Organization created with an explicit Owner membership.");
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
      label="New workspace"
      fields={["name", "slug"]}
      submit={async (values) => {
        await run(async () => {
          await api.createWorkspace(actor, organizationId, {
            name: values.name ?? "",
            slug: values.slug ?? "",
          });
          await reload();
        }, "Workspace created in the active organization.");
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
      label="New project"
      fields={["name", "slug", "description"]}
      submit={async (values) => {
        await run(async () => {
          await api.createProject(actor, workspaceId, {
            name: values.name ?? "",
            slug: values.slug ?? "",
            description: values.description ?? "",
          });
          await reload();
        }, "Draft project created from persisted API state.");
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
      label="Edit project"
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
        }, "Project updated with optimistic concurrency control.");
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
        Add member
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
            }, "Project membership granted from the server-side role policy.");
          }}
        >
          <label>
            Principal
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
            Role
            <select
              value={role}
              onChange={(event) => {
                setRole(event.target.value);
              }}
            >
              <option>PROJECT_OWNER</option>
              <option>PROJECT_EDITOR</option>
              <option>PROJECT_VIEWER</option>
              <option>PACKAGE_OPERATOR</option>
              <option>AUDITOR</option>
            </select>
          </label>
          <button type="submit">Grant role</button>
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
              {field}
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
          <button type="submit">Save</button>
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
  return <span className={`state-badge ${state.toLowerCase()}`}>{state}</span>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function ForbiddenState({ text }: { text: string }) {
  return (
    <div className="forbidden-state">
      <strong>Scope restricted</strong>
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
      <p className="section-label">FORGEOPS / LOCAL SYNTHETIC</p>
      <h1>{title}</h1>
      <p>{detail}</p>
      {action}
    </main>
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
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}
