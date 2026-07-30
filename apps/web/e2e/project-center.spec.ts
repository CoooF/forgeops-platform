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
  await form.getByLabel("name").fill(values.name);
  await form.getByLabel("slug").fill(values.slug);
  if (values.description !== undefined) {
    await form.getByLabel("description").fill(values.description);
  }
  await form.getByRole("button", { name: "Save" }).click();
}

test("Owner creates scope and binds a package; Viewer remains read-only; archive persists", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("Project Center", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Development adapter only", { exact: false }),
  ).toBeVisible();

  await completePopover(page, "Create organization", {
    name: "Synthetic Operations",
    slug: "synthetic-operations",
  });
  await expect(page.getByLabel("Organization")).toContainText(
    "Synthetic Operations",
  );

  await completePopover(page, "New workspace", {
    name: "Advisory Lab",
    slug: "advisory-lab",
  });
  await expect(page.getByLabel("Workspace")).toContainText("Advisory Lab");

  await completePopover(page, "New project", {
    name: "Evidence Project",
    slug: "evidence-project",
    description: "SYNTHETIC project for browser authorization evidence",
  });
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toBeVisible();

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
  await page.getByRole("button", { name: "packages" }).click();
  await expect(
    page.getByText("steel-cord-scheduling", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Bind", exact: true }).click();
  await expect(
    page.getByText("Scenario installation bound", { exact: false }),
  ).toBeVisible();

  await page.getByRole("button", { name: "members" }).click();
  await page.getByRole("button", { name: "Add member" }).click();
  await page
    .locator(".popover-form")
    .getByRole("button", { name: "Grant role" })
    .click();
  await expect(page.locator(".popover-form")).toHaveCount(0);
  await expect(
    page.locator(".record-row").filter({ hasText: "Local Viewer" }),
  ).toBeVisible();

  await page.getByLabel("Synthetic principal").selectOption("local-viewer");
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "overview" }).click();
  await expect(page.getByText("Read-only project access.")).toBeVisible();
  await page.getByRole("button", { name: "packages" }).click();
  await expect(
    page.getByRole("button", { name: "Bind", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "members" }).click();
  await expect(page.getByRole("button", { name: "Add member" })).toHaveCount(0);

  await page.getByLabel("Synthetic principal").selectOption("local-outsider");
  await expect(page.getByLabel("Organization")).toContainText(
    "No visible organizations",
  );
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toHaveCount(0);

  await page.getByLabel("Synthetic principal").selectOption("local-owner");
  await expect(
    page.getByRole("heading", { name: "Evidence Project" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "overview" }).click();
  await page.getByRole("button", { name: "Archive project" }).click();
  await expect(
    page.locator(".state-badge", { hasText: "ARCHIVED" }).first(),
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
  await expect(
    page.locator(".state-badge", { hasText: "ARCHIVED" }).first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit project" })).toHaveCount(
    0,
  );
});
