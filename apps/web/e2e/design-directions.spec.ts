import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

const directions = [
  { id: "precision", code: "A", name: "静默控制台" },
  { id: "semantic", code: "B", name: "Agent 协同中枢" },
  { id: "investigation", code: "C", name: "领域蓝图" },
] as const;

test("EPIC-02.7 directions are comparable, bounded, and fit 1440x900", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const pageErrors: string[] = [];
  const apiRequests: string[] = [];
  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });
  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith("/v1/") || pathname.startsWith("/health/")) {
      apiRequests.push(pathname);
    }
  });
  const screenshotDirectory = path.resolve(
    process.cwd(),
    "../../docs/product-design/epic-02.7/screenshots",
  );
  mkdirSync(screenshotDirectory, { recursive: true });

  for (const direction of directions) {
    await page.goto(`/design-preview/directions?direction=${direction.id}`);
    await expect(page.getByTestId(`direction-${direction.id}`)).toBeVisible();
    await expect(
      page.getByText(direction.name, { exact: true }).last(),
    ).toBeVisible();
    await expect(page.getByTestId("prototype-boundary")).toContainText(
      "未接 Workflow / Run / Agent 后端",
    );
    await expect(page.getByText("未运行 · 建议未执行")).toBeVisible();
    await expect(page.locator(".global-product-nav > button")).toHaveCount(8);
    await expect(page.getByText("数据与数据库", { exact: true })).toBeVisible();
    await expect(
      page.getByText("主 Agent 中心", { exact: true }),
    ).toBeVisible();
    const dataModuleTrigger = page
      .locator(".global-product-nav")
      .getByRole("button", { name: /数据与数据库/ });
    await dataModuleTrigger.click();
    await expect(
      page.getByRole("dialog", { name: "数据与数据库模块预览" }),
    ).toContainText("数据源与数据库实例");
    await expect(
      page.getByRole("dialog", { name: "数据与数据库模块预览" }),
    ).toContainText("未接对应后端");
    if (direction.id === "precision") {
      await page.screenshot({
        path: path.join(
          screenshotDirectory,
          "module-data-and-databases-1440x900.png",
        ),
        fullPage: false,
      });
    }
    await expect(
      page.getByRole("button", { name: "关闭模块预览" }),
    ).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("dialog", { name: "数据与数据库模块预览" }),
    ).toHaveCount(0);
    await expect(dataModuleTrigger).toBeFocused();
    await page
      .locator(".global-product-nav")
      .getByRole("button", { name: /主 Agent 中心/ })
      .click();
    await expect(
      page.getByRole("dialog", { name: "主 Agent 中心模块预览" }),
    ).toContainText("主 Agent 配置");
    if (direction.id === "precision") {
      await page.screenshot({
        path: path.join(
          screenshotDirectory,
          "module-main-agent-center-1440x900.png",
        ),
        fullPage: false,
      });
    }
    await page.getByRole("button", { name: "关闭模块预览" }).click();
    await page
      .locator(".global-product-nav")
      .getByRole("button", { name: /工作流/ })
      .click();
    await expect(page.locator(".studio-node")).toHaveCount(8);
    await expect(page.locator(".node-ports")).toHaveCount(8);
    await expect(page.getByLabel("节点与能力库")).toBeVisible();
    await expect(page.getByLabel("节点检查器")).toBeVisible();
    await expect(page.getByLabel("运行与调试控制台")).toBeVisible();
    await expect(page.getByText("主 Agent", { exact: true })).toBeVisible();
    await expect(page.getByText("失败出口尚未连接")).toBeVisible();
    await page.locator(".main-agent-entry").click();
    await expect(
      page.getByRole("dialog", { name: "主 Agent 协作预览" }),
    ).toContainText("未调用模型");
    await page.locator(".main-agent-entry").click();

    const overflow = await page.evaluate(() => ({
      page:
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
      canvas: Array.from(document.querySelectorAll(".studio-node")).some(
        (node) => {
          const item = node.getBoundingClientRect();
          const canvas = node.closest(".canvas-area")?.getBoundingClientRect();
          return canvas
            ? item.right > canvas.right || item.bottom > canvas.bottom
            : true;
        },
      ),
    }));
    expect(overflow.page).toBe(0);
    expect(overflow.canvas).toBe(false);

    await page.screenshot({
      path: path.join(
        screenshotDirectory,
        `direction-${direction.code.toLowerCase()}-${direction.id}-1440x900.png`,
      ),
      fullPage: false,
    });
  }
  expect(pageErrors).toEqual([]);
  expect(apiRequests).toEqual([]);
});

test("EPIC-02.7 directions reflow without horizontal scroll and respect reduced motion", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 375, height: 812 });

  for (const direction of directions) {
    await page.goto(`/design-preview/directions?direction=${direction.id}`);
    await expect(page.getByTestId(`direction-${direction.id}`)).toBeVisible();
    const viewportState = await page.evaluate(() => ({
      overflow:
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
      reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)")
        .matches,
    }));
    expect(viewportState.overflow).toBe(0);
    expect(viewportState.reducedMotion).toBe(true);
  }
});
