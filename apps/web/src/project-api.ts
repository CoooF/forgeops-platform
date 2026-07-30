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

function idempotencyHeaders(): HeadersInit {
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
