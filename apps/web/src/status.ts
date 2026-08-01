export interface PlatformStatus {
  environment: "DEV" | "TEST" | "INT" | "PREPROD" | "PROD";
  scope: "LOCAL_SYNTHETIC_ENGINEERING";
  advisoryMode: true;
  dataMode: "SYNTHETIC_ONLY";
  externalModelEnabled: false;
  runtimePluginsEnabled: false;
  actionAdapter: "MOCK" | "DENY_ALL";
  sdkVersion: string;
  enterpriseApproval: "NOT_GRANTED";
  identityMode: "LOCAL_SYNTHETIC";
  enterpriseIdentityConnected: false;
  projectScopeEnabled: true;
  semanticRuntimeEnabled: true;
  knowledgeHubEnabled: true;
  contextCompilerEnabled: true;
  groundingValidationEnabled: true;
  agentRuntimeEnabled: false;
  llmEnabled: false;
  ragEnabled: false;
  workflowRuntimeEnabled: false;
}

export interface Installation {
  installationId: string;
  packageId: string;
  packageVersion: string;
  state: string;
  contentDigest: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function assertPlatformStatus(value: unknown): PlatformStatus {
  if (
    !isRecord(value) ||
    value.scope !== "LOCAL_SYNTHETIC_ENGINEERING" ||
    value.advisoryMode !== true ||
    value.dataMode !== "SYNTHETIC_ONLY" ||
    value.externalModelEnabled !== false ||
    value.runtimePluginsEnabled !== false ||
    value.enterpriseApproval !== "NOT_GRANTED" ||
    value.identityMode !== "LOCAL_SYNTHETIC" ||
    value.enterpriseIdentityConnected !== false ||
    value.projectScopeEnabled !== true ||
    value.semanticRuntimeEnabled !== true ||
    value.knowledgeHubEnabled !== true ||
    value.contextCompilerEnabled !== true ||
    value.groundingValidationEnabled !== true ||
    value.agentRuntimeEnabled !== false ||
    value.llmEnabled !== false ||
    value.ragEnabled !== false ||
    value.workflowRuntimeEnabled !== false
  ) {
    throw new Error("unsafe or incompatible platform status response");
  }
  return value as unknown as PlatformStatus;
}

export async function fetchPlatformState(): Promise<{
  status: PlatformStatus;
  installations: Installation[];
}> {
  const headers = { "X-ForgeOps-Actor": "local-web-shell" };
  const [statusResponse, installationsResponse] = await Promise.all([
    fetch("/v1/platform/status", { headers }),
    fetch("/v1/scenario-package-installations", { headers }),
  ]);
  if (!statusResponse.ok || !installationsResponse.ok) {
    throw new Error("ForgeOps API state is unavailable");
  }
  const status: unknown = await statusResponse.json();
  const installations: unknown = await installationsResponse.json();
  if (!Array.isArray(installations)) {
    throw new Error("invalid installation response");
  }
  return {
    status: assertPlatformStatus(status),
    installations: installations as Installation[],
  };
}
