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
  await page.getByRole("button", { name: "校验并登记" }).click();
  await expect(
    page.getByText("已通过后端严格校验并完成登记", {
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
    .getByLabel("组织", { exact: true })
    .selectOption(organization.organizationId);
  await page
    .getByLabel("工作空间", { exact: true })
    .selectOption(workspace.workspaceId);
  await page.getByRole("button", { name: "领域资产" }).click();
  await expect(
    page.getByRole("heading", { name: "领域资产注册中心" }),
  ).toBeVisible();
  await expect(page.getByText("尚未完成企业验证")).toBeVisible();

  await registerThroughUi(page, loadExample("core-semantics.component.json"));
  await registerThroughUi(page, loadExample("reference-domain-a.domain.json"));
  await registerThroughUi(page, domainVersionTwo());

  await page
    .getByLabel("领域安装根包")
    .selectOption({ label: "org.forgeops.domain.reference-a@0.1.0" });
  await page.getByRole("button", { name: "预览依赖锁" }).click();
  await expect(page.getByText("未提交的依赖预览")).toBeVisible();
  await expect(
    page.getByText("未创建运行状态", { exact: false }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "安装为未启用" }).click();
  await expect(
    page.getByText("已安装为“未启用”状态", { exact: false }),
  ).toBeVisible();

  await page
    .getByLabel("领域安装根包")
    .selectOption({ label: "org.forgeops.domain.reference-a@0.2.0" });
  await page.getByRole("button", { name: "预览依赖锁" }).click();
  await page.getByRole("button", { name: "安装为未启用" }).click();

  await page.reload();
  await page
    .getByLabel("组织", { exact: true })
    .selectOption(organization.organizationId);
  await page
    .getByLabel("工作空间", { exact: true })
    .selectOption(workspace.workspaceId);
  await page.getByRole("button", { name: "领域锁", exact: true }).click();
  await page.getByLabel("项目领域锁安装版本").selectOption({ index: 1 });
  await page.getByRole("button", { name: "创建当前领域锁" }).click();
  await expect(page.getByTestId("current-domain-lock")).toContainText(
    "org.forgeops.domain.reference-a",
  );

  await page.getByLabel("项目领域锁安装版本").selectOption({ index: 2 });
  await expect(page.getByTestId("domain-lock-diff")).toContainText("变更 1");
  await page.getByRole("button", { name: "确认切换版本" }).click();
  await expect(page.getByTestId("current-domain-lock")).toContainText("0.2.0");
  await expect(page.locator(".lock-history-row")).toHaveCount(2);
  await expect(page.locator(".lock-history-row").last()).toContainText(
    "历史版本",
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
  await page.getByLabel("演示角色").selectOption("local-viewer");
  await page.getByRole("button", { name: "领域锁", exact: true }).click();
  await expect(page.getByTestId("current-domain-lock")).toBeVisible();
  await expect(page.getByLabel("项目领域锁安装版本")).toHaveCount(0);
  await expect(
    page.getByText("只能查看领域锁摘要", { exact: false }),
  ).toBeVisible();

  await page.getByLabel("演示角色").selectOption("local-owner");
  await page.getByRole("button", { name: "领域资产" }).click();
  await page
    .getByRole("button", {
      name: /org\.forgeops\.component\.core-semantics/,
    })
    .click();
  await page.getByRole("button", { name: "撤回版本" }).click();
  await expect(page.getByTestId("package-impact")).toContainText(
    "2 个组织安装",
  );
  await expect(page.getByTestId("package-impact")).toContainText(
    "2 个项目领域锁",
  );

  await page.reload();
  await page
    .getByLabel("组织", { exact: true })
    .selectOption(organization.organizationId);
  await page
    .getByLabel("工作空间", { exact: true })
    .selectOption(workspace.workspaceId);
  await page.getByRole("button", { name: "领域锁", exact: true }).click();
  await expect(page.getByTestId("current-domain-lock")).toContainText(
    "存在风险",
  );
  await page.getByLabel("项目领域锁安装版本").selectOption({ index: 2 });
  await page.getByRole("button", { name: "确认切换版本" }).click();
  await expect(
    page.getByText("WITHDRAWN_OR_QUARANTINED_DEPENDENCY", { exact: false }),
  ).toBeVisible();
  await expect(page.getByTestId("current-domain-lock")).toContainText("0.2.0");
});
