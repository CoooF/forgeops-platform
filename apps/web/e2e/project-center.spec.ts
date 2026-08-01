import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

const ownerHeaders = {
  "X-ForgeOps-Actor": "local-owner",
  "X-Trace-ID": "playwright-owner-trace",
};

async function completePopover(
  page: Page,
  buttonName: string,
  values: { name: string; slug: string; description?: string },
) {
  await page.getByRole("button", { name: buttonName }).click();
  const form = page.locator(".popover-form");
  await form.getByLabel("名称").fill(values.name);
  await form.getByLabel("唯一标识").fill(values.slug);
  if (values.description !== undefined) {
    await form.getByLabel("说明").fill(values.description);
  }
  await form.getByRole("button", { name: "保存" }).click();
}

test("Owner creates scope and binds a package; Viewer remains read-only; archive persists", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("项目中心", { exact: true })).toBeVisible();
  await expect(
    page.getByText("本地工程身份只用于验证权限差异", { exact: false }),
  ).toBeVisible();

  await completePopover(page, "创建组织", {
    name: "Synthetic Operations",
    slug: "synthetic-operations",
  });
  await expect(page.getByLabel("组织", { exact: true })).toContainText(
    "Synthetic Operations",
  );

  await completePopover(page, "新建工作空间", {
    name: "Advisory Lab",
    slug: "advisory-lab",
  });
  await expect(page.getByLabel("工作空间", { exact: true })).toContainText(
    "Advisory Lab",
  );

  await completePopover(page, "新建项目", {
    name: "Evidence Project",
    slug: "evidence-project",
    description: "SYNTHETIC project for browser authorization evidence",
  });
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toBeVisible();
  const organizationId = await page
    .getByLabel("组织", { exact: true })
    .inputValue();
  const workspaceId = await page
    .getByLabel("工作空间", { exact: true })
    .inputValue();

  const packageRoot = path.resolve(
    process.cwd(),
    "../../scenario-packages/steel-cord-scheduling",
  );
  const manifest = JSON.parse(
    readFileSync(path.join(packageRoot, "manifest.json"), "utf8"),
  ) as {
    permissions: string[];
  };
  const artifactPayloadBase64 = readFileSync(
    path.join(packageRoot, "artifact.json"),
  ).toString("base64");
  const installed = await page.request.post(
    "/v1/scenario-package-installations",
    {
      headers: ownerHeaders,
      data: { manifest, artifactPayloadBase64 },
    },
  );
  expect(installed.status()).toBe(201);
  const installation = (await installed.json()) as { installationId: string };
  expect(
    (
      await page.request.post(
        `/v1/scenario-package-installations/${installation.installationId}:mark-tested`,
        { headers: ownerHeaders },
      )
    ).ok(),
  ).toBe(true);
  expect(
    (
      await page.request.post(
        `/v1/scenario-package-installations/${installation.installationId}:approve`,
        { headers: ownerHeaders },
      )
    ).ok(),
  ).toBe(true);
  expect(
    (
      await page.request.post(
        `/v1/scenario-package-installations/${installation.installationId}/permission-grants`,
        { headers: ownerHeaders, data: { permissions: manifest.permissions } },
      )
    ).ok(),
  ).toBe(true);

  await page.reload();
  await page.getByLabel("组织", { exact: true }).selectOption(organizationId);
  await page.getByLabel("工作空间", { exact: true }).selectOption(workspaceId);
  await page.getByRole("button", { name: "场景包" }).click();
  await expect(
    page.getByText("steel-cord-scheduling", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "绑定", exact: true }).click();
  await expect(
    page.getByText("场景包安装版本已绑定", { exact: false }),
  ).toBeVisible();

  await page.getByRole("button", { name: "成员权限" }).click();
  await page.getByRole("button", { name: "添加成员" }).click();
  await page
    .locator(".popover-form")
    .getByRole("button", { name: "确认授权" })
    .click();
  await expect(page.locator(".popover-form")).toHaveCount(0);
  await expect(
    page.locator(".record-row").filter({ hasText: "Local Viewer" }),
  ).toBeVisible();

  await page.getByLabel("演示角色").selectOption("local-viewer");
  await page.getByLabel("组织", { exact: true }).selectOption(organizationId);
  await page.getByLabel("工作空间", { exact: true }).selectOption(workspaceId);
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "项目概览" }).click();
  await expect(page.getByText("当前身份仅可查看此项目。")).toBeVisible();
  await page.getByRole("button", { name: "场景包" }).click();
  await expect(
    page.getByRole("button", { name: "绑定", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "成员权限" }).click();
  await expect(page.getByRole("button", { name: "添加成员" })).toHaveCount(0);

  await page.getByLabel("演示角色").selectOption("local-outsider");
  await expect(page.getByLabel("组织", { exact: true })).toContainText(
    "尚未创建组织",
  );
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toHaveCount(0);

  await page.getByLabel("演示角色").selectOption("local-owner");
  await page.getByLabel("组织", { exact: true }).selectOption(organizationId);
  await page.getByLabel("工作空间", { exact: true }).selectOption(workspaceId);
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "项目概览" }).click();
  await page.getByRole("button", { name: "归档项目" }).click();
  await expect(
    page.locator(".state-badge", { hasText: "已归档" }).first(),
  ).toBeVisible();
  const projectId = await page.locator(".detail-heading code").textContent();
  if (!projectId) throw new Error("project ID was not rendered");
  const blocked = await page.request.post(
    `/v1/projects/${projectId}/package-bindings`,
    {
      headers: {
        ...ownerHeaders,
        "Idempotency-Key": "archived-binding-attempt",
      },
      data: { installationId: installation.installationId },
    },
  );
  expect(blocked.status()).toBe(409);
  const blockedPayload = (await blocked.json()) as { error: { code: string } };
  expect(blockedPayload.error.code).toBe("ILLEGAL_STATE_TRANSITION");

  await page.reload();
  await page.getByLabel("组织", { exact: true }).selectOption(organizationId);
  await page.getByLabel("工作空间", { exact: true }).selectOption(workspaceId);
  await expect(
    page.locator(".state-badge", { hasText: "已归档" }).first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "编辑项目" })).toHaveCount(0);
});
