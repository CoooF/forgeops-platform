import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

const directions = [
  { id: "precision", code: "A", name: "精密工业工作台" },
  { id: "semantic", code: "B", name: "领域建模台" },
  { id: "investigation", code: "C", name: "运行推演台" },
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
    await expect(page.locator(".studio-node")).toHaveCount(8);
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
