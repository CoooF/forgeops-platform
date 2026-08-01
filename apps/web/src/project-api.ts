import { assertPlatformStatus, type PlatformStatus } from "./status";

export const LOCAL_ACTORS = [
  { value: "local-owner", label: "Local Owner" },
  { value: "local-editor", label: "Local Editor" },
  { value: "local-viewer", label: "Local Viewer" },
  { value: "local-outsider", label: "Local Outsider" },
  { value: "local-disabled", label: "Disabled Principal" },
] as const;

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Principal {
  principalId: string;
  subjectRef: string;
  displayName: string;
  state: "ACTIVE" | "DISABLED";
}

export interface Membership {
  membershipId: string;
  principalId: string;
  scopeType: "PLATFORM" | "ORGANIZATION" | "WORKSPACE" | "PROJECT";
  scopeId: string | null;
  role: string;
  state: "ACTIVE" | "SUSPENDED" | "REVOKED";
  version: number;
  principal?: Pick<Principal, "subjectRef" | "displayName" | "state">;
}

export interface Me {
  principal: Principal;
  authenticationMode: "LOCAL_SYNTHETIC";
  enterpriseIdentityConnected: false;
  memberships: Membership[];
}

export interface Organization {
  organizationId: string;
  name: string;
  slug: string;
  state: "ACTIVE" | "SUSPENDED" | "ARCHIVED";
  version: number;
}

export interface Workspace {
  workspaceId: string;
  organizationId: string;
  name: string;
  slug: string;
  state: "ACTIVE" | "ARCHIVED";
  version: number;
}

export interface Project {
  projectId: string;
  workspaceId: string;
  name: string;
  slug: string;
  description: string;
  state: "DRAFT" | "ACTIVE" | "ARCHIVED";
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectBinding {
  bindingId: string;
  projectId: string;
  installationId: string;
  packageKind: "SCENARIO";
  state: "ACTIVE" | "DISABLED" | "REVOKED";
  version: number;
  packageId: string;
  packageVersion: string;
  installationState: string;
}

export interface BindableInstallation {
  installationId: string;
  packageId: string;
  packageVersion: string;
  state: string;
  alreadyBound: boolean;
}

export interface AuditEvent {
  eventId: string;
  eventType: string;
  actorRef: string;
  resourceRef: string;
  result: string;
  reasonCode: string;
  occurredAt: string;
  traceId: string;
  scopeRef: string;
  policyVersion: string;
}

export interface HealthSummary {
  health: "HEALTHY_FOR_SELECTION" | "AT_RISK" | "BLOCKED_FOR_NEW_USE";
  reasons: string[];
}

export interface FdsPackageVersion {
  packageVersionId: string;
  immutableFacts: {
    packageVersionId: string;
    packageId: string;
    packageVersion: string;
    kind: "DOMAIN" | "ORGANIZATION_OVERLAY" | "SCENARIO" | "COMPONENT";
    componentKind: string | null;
    manifest: Record<string, unknown>;
    normalizedManifest: string;
    manifestDigest: string;
    contentDigest: string;
    artifactRef: string;
    sbomRef: string;
    signatureRef: string;
    publisher: string;
    namespaceOwner: string;
    licenseId: string;
    licenseVerified: boolean;
    provenanceRef: string;
    provenanceDigest: string;
    visibility: string;
    contentClassification: string;
    trustTier: string;
    ownerOrganizationId: string | null;
    createdBy: string;
    createdAt: string;
  };
  governance: {
    state: "REGISTERED_VALIDATED" | "QUARANTINED" | "WITHDRAWN";
    reason: string | null;
    governedAt: string | null;
    updatedAt: string;
    version: number;
  };
  trustBoundary: "NOT_ENTERPRISE_VERIFIED";
  runtimeCapabilityEnabled: false;
}

export interface PackageVersionRef {
  packageVersionId: string;
  packageId: string;
  packageVersion: string;
  kind: string;
  componentKind: string | null;
  manifestDigest: string;
  contentDigest: string;
}

export interface DependencyLock {
  lockDigest: string;
  rootPackageId: string;
  rootPackageVersion: string;
  nodes: Array<{
    packageId: string;
    packageVersion: string;
    kind: string;
    contentDigest: string;
  }>;
  edges: Array<{
    fromPackageId: string;
    toPackageId: string;
    versionConstraint: string;
    required: boolean;
  }>;
  requestedPermissions: string[];
  permissionDelta: string[];
  resourceBudget: Record<string, number | boolean | string[]>;
  resourceBudgetDelta: Record<string, number | boolean | string[]>;
}

export interface DomainInstallation {
  installationId: string;
  immutableFacts: {
    installationId: string;
    organizationId: string;
    rootPackageVersionId: string;
    rootPackageId: string;
    rootPackageVersion: string;
    rootKind: "DOMAIN" | "ORGANIZATION_OVERLAY";
    dependencyLock: DependencyLock;
    lockDigest: string;
    packageVersionRefs: PackageVersionRef[];
    requestedPermissions: string[];
    permissionDelta: string[];
    resourceBudget: Record<string, number | boolean | string[]>;
    resourceBudgetDelta: Record<string, number | boolean | string[]>;
    authorizationEffect: "NONE";
    runtimeStateCreated: false;
    semanticRuntimeReady: false;
    createdBy: string;
    createdAt: string;
  };
  installationState: {
    state:
      "INSTALLED_DISABLED" | "DISABLED" | "REVOKED" | "LOGICALLY_UNINSTALLED";
    reason: string | null;
    updatedAt: string;
    version: number;
  };
  derivedHealth: HealthSummary;
}

export interface ProjectDomainLock {
  projectDomainLockId: string;
  immutableFacts: {
    projectDomainLockId: string;
    projectId: string;
    organizationId: string;
    installationId: string;
    rootPackageId: string;
    rootPackageVersion: string;
    rootKind: string;
    dependencyLock: DependencyLock;
    lockDigest: string;
    packageVersionRefs: PackageVersionRef[];
    requestedPermissions: string[];
    permissionDelta: string[];
    resourceBudget: Record<string, number | boolean | string[]>;
    resourceBudgetDelta: Record<string, number | boolean | string[]>;
    purpose: string;
    previousLockId: string | null;
    runtimeBindingCreated: false;
    authorizationEffect: "NONE";
    semanticRuntimeReady: false;
    createdBy: string;
    createdAt: string;
  };
  lockState: { status: "CURRENT" | "SUPERSEDED" | "REVOKED"; version: number };
  derivedHealth: HealthSummary;
}

export interface DomainLockDiff {
  added: Array<Record<string, string | null>>;
  removed: Array<Record<string, string | null>>;
  changed: Array<Record<string, string | null>>;
  permissionsAdded: string[];
  permissionsRemoved: string[];
  budgetDelta: Record<string, number | boolean>;
  visibilityTrustChanges: string[];
  semanticDifferenceStatus: "NOT_EVALUATED";
}

export interface PackageImpact {
  packageVersionId: string;
  packageId: string;
  packageVersion: string;
  registryState: string;
  installations: Array<{
    installationId: string;
    organizationId: string;
    rootPackageId: string;
    state: string;
  }>;
  projectDomainLocks: Array<{
    projectDomainLockId: string;
    projectId: string;
    organizationId: string;
    status: string;
  }>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function request<T>(
  path: string,
  actor: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("X-ForgeOps-Actor", actor);
  headers.set("X-Trace-ID", crypto.randomUUID().replaceAll("-", ""));
  const response = await fetch(path, {
    ...init,
    headers,
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    const error =
      isRecord(payload) && isRecord(payload.error) ? payload.error : {};
    throw new ApiError(
      response.status,
      typeof error.code === "string" ? error.code : "API_ERROR",
      typeof error.message === "string"
        ? error.message
        : "ForgeOps API request failed",
    );
  }
  return payload as T;
}

function idempotencyHeaders(): Record<string, string> {
  return { "Idempotency-Key": crypto.randomUUID() };
}

export async function loadSession(actor: string): Promise<{
  status: PlatformStatus;
  me: Me;
  organizations: Organization[];
}> {
  const [status, me, organizations] = await Promise.all([
    request<unknown>("/v1/platform/status", actor),
    request<Me>("/v1/me", actor),
    request<Page<Organization>>("/v1/organizations?limit=100", actor),
  ]);
  return {
    status: assertPlatformStatus(status),
    me,
    organizations: organizations.items,
  };
}

export const api = {
  workspaces: (actor: string, organizationId: string) =>
    request<Page<Workspace>>(
      `/v1/organizations/${organizationId}/workspaces?limit=100`,
      actor,
    ),
  projects: (actor: string, workspaceId: string) =>
    request<Page<Project>>(
      `/v1/workspaces/${workspaceId}/projects?limit=100`,
      actor,
    ),
  projectPermissions: (actor: string, projectId: string) =>
    request<{ permissions: string[] }>(
      `/v1/projects/${projectId}/permissions`,
      actor,
    ),
  projectMembers: (actor: string, projectId: string) =>
    request<Page<Membership>>(
      `/v1/projects/${projectId}/memberships?limit=100`,
      actor,
    ),
  projectBindings: (actor: string, projectId: string) =>
    request<Page<ProjectBinding>>(
      `/v1/projects/${projectId}/package-bindings?limit=100`,
      actor,
    ),
  bindableInstallations: (actor: string, projectId: string) =>
    request<Page<BindableInstallation>>(
      `/v1/projects/${projectId}/bindable-installations?limit=100`,
      actor,
    ),
  projectAudit: (actor: string, projectId: string) =>
    request<Page<AuditEvent>>(
      `/v1/projects/${projectId}/audit-events?limit=100`,
      actor,
    ),
  createOrganization: (actor: string, body: { name: string; slug: string }) =>
    request<Organization>("/v1/organizations", actor, {
      method: "POST",
      headers: idempotencyHeaders(),
      body: JSON.stringify(body),
    }),
  createWorkspace: (
    actor: string,
    organizationId: string,
    body: { name: string; slug: string },
  ) =>
    request<Workspace>(
      `/v1/organizations/${organizationId}/workspaces`,
      actor,
      {
        method: "POST",
        headers: idempotencyHeaders(),
        body: JSON.stringify(body),
      },
    ),
  createProject: (
    actor: string,
    workspaceId: string,
    body: { name: string; slug: string; description: string },
  ) =>
    request<Project>(`/v1/workspaces/${workspaceId}/projects`, actor, {
      method: "POST",
      headers: idempotencyHeaders(),
      body: JSON.stringify(body),
    }),
  updateProject: (
    actor: string,
    project: Project,
    body: { name: string; slug: string; description: string },
  ) =>
    request<Project>(`/v1/projects/${project.projectId}`, actor, {
      method: "PATCH",
      body: JSON.stringify({ ...body, expectedVersion: project.version }),
    }),
  transitionProject: (
    actor: string,
    project: Project,
    transition: "activate" | "archive",
  ) =>
    request<Project>(`/v1/projects/${project.projectId}:${transition}`, actor, {
      method: "POST",
      body: JSON.stringify({ expectedVersion: project.version }),
    }),
  createProjectMembership: (
    actor: string,
    organizationId: string,
    projectId: string,
    principalRef: string,
    role: string,
  ) =>
    request<Membership>(
      `/v1/organizations/${organizationId}/memberships`,
      actor,
      {
        method: "POST",
        headers: idempotencyHeaders(),
        body: JSON.stringify({
          principalRef,
          scopeType: "PROJECT",
          scopeId: projectId,
          role,
        }),
      },
    ),
  transitionMembership: (
    actor: string,
    membership: Membership,
    transition: "suspend" | "revoke",
  ) =>
    request<Membership>(
      `/v1/memberships/${membership.membershipId}:${transition}`,
      actor,
      {
        method: "POST",
        body: JSON.stringify({ expectedVersion: membership.version }),
      },
    ),
  bindPackage: (actor: string, projectId: string, installationId: string) =>
    request<ProjectBinding>(
      `/v1/projects/${projectId}/package-bindings`,
      actor,
      {
        method: "POST",
        headers: idempotencyHeaders(),
        body: JSON.stringify({ installationId }),
      },
    ),
  disableBinding: (actor: string, binding: ProjectBinding) =>
    request<ProjectBinding>(
      `/v1/project-package-bindings/${binding.bindingId}:disable`,
      actor,
      {
        method: "POST",
        body: JSON.stringify({ expectedVersion: binding.version }),
      },
    ),
  fdsPackageVersions: (
    actor: string,
    filters: { kind?: string; state?: string; visibility?: string } = {},
  ) => {
    const query = new URLSearchParams({ limit: "100" });
    if (filters.kind) query.set("kind", filters.kind);
    if (filters.state) query.set("state", filters.state);
    if (filters.visibility) query.set("visibility", filters.visibility);
    return request<Page<FdsPackageVersion>>(
      `/v1/fds/package-versions?${query.toString()}`,
      actor,
    );
  },
  registerFdsPackageVersion: (
    actor: string,
    manifest: Record<string, unknown>,
    ownerOrganizationId?: string,
  ) =>
    request<FdsPackageVersion>("/v1/fds/package-versions", actor, {
      method: "POST",
      headers: idempotencyHeaders(),
      body: JSON.stringify({ manifest, ownerOrganizationId }),
    }),
  transitionFdsPackageVersion: (
    actor: string,
    item: FdsPackageVersion,
    transition: "quarantine" | "withdraw",
    reason: string,
  ) =>
    request<FdsPackageVersion>(
      `/v1/fds/package-versions/${item.packageVersionId}:${transition}`,
      actor,
      {
        method: "POST",
        headers: {
          ...idempotencyHeaders(),
          "If-Match": String(item.governance.version),
        },
        body: JSON.stringify({ reason }),
      },
    ),
  fdsPackageImpacts: (actor: string, packageVersionId: string) =>
    request<PackageImpact>(
      `/v1/fds/package-versions/${packageVersionId}/impacts`,
      actor,
    ),
  domainInstallations: (actor: string, organizationId: string) =>
    request<Page<DomainInstallation>>(
      `/v1/organizations/${organizationId}/domain-installations?limit=100`,
      actor,
    ),
  previewDomainInstallation: (
    actor: string,
    organizationId: string,
    rootPackageVersionId: string,
  ) =>
    request<DomainInstallation>(
      `/v1/organizations/${organizationId}/domain-installations:preview`,
      actor,
      {
        method: "POST",
        body: JSON.stringify({
          rootPackageVersionId,
          targetVersions: {
            platform: "0.1.0",
            fds: "0.1.0",
            scenarioSdk: "0.1.0",
          },
          includeOptional: false,
        }),
      },
    ),
  createDomainInstallation: (
    actor: string,
    organizationId: string,
    rootPackageVersionId: string,
  ) =>
    request<DomainInstallation>(
      `/v1/organizations/${organizationId}/domain-installations`,
      actor,
      {
        method: "POST",
        headers: idempotencyHeaders(),
        body: JSON.stringify({
          rootPackageVersionId,
          targetVersions: {
            platform: "0.1.0",
            fds: "0.1.0",
            scenarioSdk: "0.1.0",
          },
          includeOptional: false,
        }),
      },
    ),
  transitionDomainInstallation: (
    actor: string,
    installation: DomainInstallation,
    transition: "disable" | "revoke" | "logical-uninstall",
    reason: string,
  ) =>
    request<DomainInstallation>(
      `/v1/domain-installations/${installation.installationId}:${transition}`,
      actor,
      {
        method: "POST",
        headers: {
          ...idempotencyHeaders(),
          "If-Match": String(installation.installationState.version),
        },
        body: JSON.stringify({ reason }),
      },
    ),
  projectDomainInstallations: (actor: string, projectId: string) =>
    request<Page<DomainInstallation>>(
      `/v1/projects/${projectId}/domain-installations`,
      actor,
    ),
  projectDomainLocks: (actor: string, projectId: string) =>
    request<Page<ProjectDomainLock>>(
      `/v1/projects/${projectId}/domain-locks?limit=100`,
      actor,
    ),
  currentProjectDomainLock: (actor: string, projectId: string) =>
    request<ProjectDomainLock | null>(
      `/v1/projects/${projectId}/domain-locks/current`,
      actor,
    ),
  compareDomainInstallations: (
    actor: string,
    fromInstallationId: string,
    toInstallationId: string,
  ) =>
    request<DomainLockDiff>(
      `/v1/domain-installations/${fromInstallationId}:compare`,
      actor,
      { method: "POST", body: JSON.stringify({ toInstallationId }) },
    ),
  createProjectDomainLock: (
    actor: string,
    projectId: string,
    installationId: string,
    purpose: string,
  ) =>
    request<ProjectDomainLock>(
      `/v1/projects/${projectId}/domain-locks`,
      actor,
      {
        method: "POST",
        headers: idempotencyHeaders(),
        body: JSON.stringify({ installationId, purpose }),
      },
    ),
};

export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404)
      return "This resource is unavailable or outside your scope.";
    if (error.status === 409)
      return `Conflict: ${error.code}. Refresh before retrying.`;
    if (error.status === 401) return `Authentication refused: ${error.code}.`;
    return `${error.code}: ${error.message}`;
  }
  return error instanceof Error ? error.message : "Unknown API error";
}
