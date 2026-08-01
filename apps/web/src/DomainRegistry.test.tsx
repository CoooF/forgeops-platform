import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DomainRegistry } from "./DomainRegistry";
import { ProjectDomainLockPanel } from "./ProjectDomainLock";
import type { DomainInstallation, ProjectDomainLock } from "./project-api";

const run = async (operation: () => Promise<void>) => operation();

describe("FDS Registry governance surfaces", () => {
  it("renders the Registry empty state with the local trust and runtime boundary", () => {
    const markup = renderToStaticMarkup(
      <DomainRegistry
        actor="local-owner"
        organizationId="organization-1"
        canRegisterPublic
        canManageOrganization
        pending={false}
        run={run}
        notice=""
        error=""
      />,
    );

    expect(markup).toContain("领域资产注册中心");
    expect(markup).toContain("还没有可见的能力包版本");
    expect(markup).toContain("尚未完成企业验证");
    expect(markup).toContain("不会自动启用运行能力");
  });

  it("renders a Viewer-safe current lock and immutable history without controls", () => {
    const lock = projectLock();
    const markup = renderToStaticMarkup(
      <ProjectDomainLockPanel
        actor="local-viewer"
        projectId="project-1"
        projectActive
        locks={[lock]}
        installations={[]}
        canManage={false}
        pending={false}
        run={run}
        reload={() => Promise.resolve()}
      />,
    );

    expect(markup).toContain("org.forgeops.domain.synthetic@0.1.0");
    expect(markup).toContain("不产生授权");
    expect(markup).toContain("未创建运行绑定");
    expect(markup).toContain("只能查看领域锁摘要");
    expect(markup).not.toContain("确认切换版本");
  });
});

function projectLock(): ProjectDomainLock {
  const installation = {
    installationId: "installation-1",
    immutableFacts: {
      installationId: "installation-1",
      organizationId: "organization-1",
      rootPackageVersionId: "package-version-1",
      rootPackageId: "org.forgeops.domain.synthetic",
      rootPackageVersion: "0.1.0",
      rootKind: "DOMAIN",
      dependencyLock: {
        lockDigest: `sha256:${"1".repeat(64)}`,
        rootPackageId: "org.forgeops.domain.synthetic",
        rootPackageVersion: "0.1.0",
        nodes: [],
        edges: [],
        requestedPermissions: [],
        permissionDelta: [],
        resourceBudget: {},
        resourceBudgetDelta: {},
      },
      lockDigest: `sha256:${"1".repeat(64)}`,
      packageVersionRefs: [
        {
          packageVersionId: "package-version-1",
          packageId: "org.forgeops.domain.synthetic",
          packageVersion: "0.1.0",
          kind: "DOMAIN",
          componentKind: null,
          manifestDigest: `sha256:${"2".repeat(64)}`,
          contentDigest: `sha256:${"3".repeat(64)}`,
        },
      ],
      requestedPermissions: [],
      permissionDelta: [],
      resourceBudget: {},
      resourceBudgetDelta: {},
      authorizationEffect: "NONE",
      runtimeStateCreated: false,
      semanticRuntimeReady: false,
      createdBy: "local-owner",
      createdAt: "2026-08-01T00:00:00Z",
    },
    installationState: {
      state: "INSTALLED_DISABLED",
      reason: null,
      updatedAt: "2026-08-01T00:00:00Z",
      version: 1,
    },
    derivedHealth: { health: "HEALTHY_FOR_SELECTION", reasons: [] },
  } satisfies DomainInstallation;

  return {
    projectDomainLockId: "project-lock-1",
    immutableFacts: {
      ...installation.immutableFacts,
      projectDomainLockId: "project-lock-1",
      projectId: "project-1",
      purpose: "Synthetic selection",
      previousLockId: null,
      runtimeBindingCreated: false,
    },
    lockState: { status: "CURRENT", version: 1 },
    derivedHealth: { health: "HEALTHY_FOR_SELECTION", reasons: [] },
  };
}
