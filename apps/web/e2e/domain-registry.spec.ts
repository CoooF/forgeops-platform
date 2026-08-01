import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

const ownerHeaders = {
  "X-ForgeOps-Actor": "local-owner",
  "X-Trace-ID": "playwright-fds-owner-trace",
};

function withKey(key: string) {
  return { ...ownerHeaders, "Idempotency-Key": key };
}

function loadExample(name: string): Record<string, unknown> {
  return JSON.parse(
    readFileSync(
      path.resolve(process.cwd(), `../../contracts/fds/examples/${name}`),
      "utf8",
    ),
  ) as Record<string, unknown>;
}

function domainVersionTwo(): Record<string, unknown> {
  const manifest = loadExample("reference-domain-a.domain.json");
  const artifact = manifest.artifact as Record<string, unknown>;
  const provenance = manifest.provenance as Record<string, unknown>;
  manifest.packageVersion = "0.2.0";
  manifest.contentDigest = `sha256:${"9".repeat(64)}`;
  artifact.contentDigest = manifest.contentDigest;
  artifact.signature = `local-sha256:${"9".repeat(64)}`;
  artifact.artifactRef =
    "local://browser-fds-fixtures/reference-domain-a-v2/artifact";
  provenance.sourceRef = "local://browser-fds-fixtures/reference-domain-a-v2";
  return manifest;
}

async function registerThroughUi(
  page: Page,
  manifest: Record<string, unknown>,
) {
  await page.getByLabel("FDS manifest JSON").fill(JSON.stringify(manifest));
  await page.getByRole("button", { name: "Validate and register" }).click();
  await expect(
    page.getByText("registered from the strict server validator", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("FDS manifest JSON")).toHaveValue("");
}

test("Owner governs real FDS locks; Viewer is read-only; withdrawal blocks new use", async ({
  page,
}) => {
  const organizationResponse = await page.request.post("/v1/organizations", {
    headers: withKey("browser-fds-organization"),
    data: { name: "Synthetic Domain Lab", slug: "synthetic-domain-lab" },
  });
  expect(organizationResponse.status()).toBe(201);
  const organization = (await organizationResponse.json()) as {
    organizationId: string;
  };
  const workspaceResponse = await page.request.post(
    `/v1/organizations/${organization.organizationId}/workspaces`,
    {
      headers: withKey("browser-fds-workspace"),
      data: { name: "Contract Workspace", slug: "contract-workspace" },
    },
  );
  expect(workspaceResponse.status()).toBe(201);
  const workspace = (await workspaceResponse.json()) as { workspaceId: string };
  const projectResponse = await page.request.post(
    `/v1/workspaces/${workspace.workspaceId}/projects`,
    {
      headers: withKey("browser-fds-project"),
      data: {
        name: "DomainLock Evidence",
        slug: "domain-lock-evidence",
        description: "SYNTHETIC browser-only DomainLock evidence",
      },
    },
  );
  expect(projectResponse.status()).toBe(201);
  const project = (await projectResponse.json()) as {
    projectId: string;
    version: number;
  };
  expect(
    (
      await page.request.post(`/v1/projects/${project.projectId}:activate`, {
        headers: ownerHeaders,
        data: { expectedVersion: project.version },
      })
    ).status(),
  ).toBe(200);

  await page.goto("/");
  await page
    .getByLabel("Organization")
    .selectOption(organization.organizationId);
  await page.getByLabel("Workspace").selectOption(workspace.workspaceId);
  await page.getByRole("button", { name: "Domain Registry" }).click();
  await expect(
    page.getByRole("heading", { name: "Domain Registry" }),
  ).toBeVisible();
  await expect(page.getByText("NOT_ENTERPRISE_VERIFIED")).toBeVisible();

  await registerThroughUi(page, loadExample("core-semantics.component.json"));
  await registerThroughUi(page, loadExample("reference-domain-a.domain.json"));
  await registerThroughUi(page, domainVersionTwo());

  await page
    .getByLabel("Installation root")
    .selectOption({ label: "org.forgeops.domain.reference-a@0.1.0" });
  await page.getByRole("button", { name: "Preview lock" }).click();
  await expect(page.getByText("Uncommitted preview")).toBeVisible();
  await expect(
    page.getByText("runtimeStateCreated=false", { exact: false }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Install disabled" }).click();
  await expect(
    page.getByText("persisted as INSTALLED_DISABLED", { exact: false }),
  ).toBeVisible();

  await page
    .getByLabel("Installation root")
    .selectOption({ label: "org.forgeops.domain.reference-a@0.2.0" });
  await page.getByRole("button", { name: "Preview lock" }).click();
  await page.getByRole("button", { name: "Install disabled" }).click();

  await page.reload();
  await page
    .getByLabel("Organization")
    .selectOption(organization.organizationId);
  await page.getByLabel("Workspace").selectOption(workspace.workspaceId);
  await page.getByRole("button", { name: "domain-lock", exact: true }).click();
  await page
    .getByLabel("Project DomainLock installation")
    .selectOption({ index: 1 });
  await page.getByRole("button", { name: "Create current lock" }).click();
  await expect(page.getByTestId("current-domain-lock")).toContainText(
    "org.forgeops.domain.reference-a",
  );

  await page
    .getByLabel("Project DomainLock installation")
    .selectOption({ index: 2 });
  await expect(page.getByTestId("domain-lock-diff")).toContainText("1 changed");
  await page.getByRole("button", { name: "Confirm lock switch" }).click();
  await expect(page.getByTestId("current-domain-lock")).toContainText("0.2.0");
  await expect(page.locator(".lock-history-row")).toHaveCount(2);
  await expect(page.locator(".lock-history-row").last()).toContainText(
    "SUPERSEDED",
  );

  const membership = await page.request.post(
    `/v1/organizations/${organization.organizationId}/memberships`,
    {
      headers: withKey("browser-fds-viewer"),
      data: {
        principalRef: "local-viewer",
        scopeType: "PROJECT",
        scopeId: project.projectId,
        role: "PROJECT_VIEWER",
      },
    },
  );
  expect(membership.status()).toBe(201);
  await page.getByLabel("Synthetic principal").selectOption("local-viewer");
  await page.getByRole("button", { name: "domain-lock", exact: true }).click();
  await expect(page.getByTestId("current-domain-lock")).toBeVisible();
  await expect(page.getByLabel("Project DomainLock installation")).toHaveCount(
    0,
  );
  await expect(
    page.getByText("Read-only DomainLock summary", { exact: false }),
  ).toBeVisible();

  await page.getByLabel("Synthetic principal").selectOption("local-owner");
  await page.getByRole("button", { name: "Domain Registry" }).click();
  await page
    .getByRole("button", {
      name: /org\.forgeops\.component\.core-semantics/,
    })
    .click();
  await page.getByRole("button", { name: "Withdraw" }).click();
  await expect(page.getByTestId("package-impact")).toContainText(
    "2 installations",
  );
  await expect(page.getByTestId("package-impact")).toContainText(
    "2 project locks",
  );

  await page.reload();
  await page
    .getByLabel("Organization")
    .selectOption(organization.organizationId);
  await page.getByLabel("Workspace").selectOption(workspace.workspaceId);
  await page.getByRole("button", { name: "domain-lock", exact: true }).click();
  await expect(page.getByTestId("current-domain-lock")).toContainText(
    "AT_RISK",
  );
  await page
    .getByLabel("Project DomainLock installation")
    .selectOption({ index: 2 });
  await page.getByRole("button", { name: "Confirm lock switch" }).click();
  await expect(
    page.getByText("WITHDRAWN_OR_QUARANTINED_DEPENDENCY", { exact: false }),
  ).toBeVisible();
  await expect(page.getByTestId("current-domain-lock")).toContainText("0.2.0");
});
