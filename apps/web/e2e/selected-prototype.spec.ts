import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

const screenshotDirectory = path.resolve(
  process.cwd(),
  "../../docs/product-design/epic-02.7/screenshots",
);

test.beforeAll(() => {
  mkdirSync(screenshotDirectory, { recursive: true });
});

test("selected direction A exposes node-private Skill/MCP assembly and a coordination-only main Agent", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const apiRequests: string[] = [];
  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith("/v1/") || pathname.startsWith("/health/")) {
      apiRequests.push(pathname);
    }
  });

  await page.goto("/design-preview/prototype?view=studio");
  await expect(page.getByTestId("prototype-boundary")).toContainText(
    "未接 Workflow / Run / Agent 后端",
  );
  await expect(page.locator(".prototype-node")).toHaveCount(7);
  await expect(page.locator(".prototype-node.type-agent")).toHaveCount(3);
  await expect(page.locator(".agent-tooling")).toContainText("节点级工具装配");
  await expect(page.locator(".agent-tooling")).toContainText("约束建模");
  await expect(page.locator(".agent-tooling")).toContainText("规则目录 MCP");
  await expect(page.locator(".agent-tooling")).toContainText(
    "这些配置只属于当前子 Agent 节点",
  );

  await page.getByRole("tab", { name: "能力", exact: true }).click();
  await expect(page.locator(".resource-library")).toContainText(
    "Skill 与 MCP 不能直接拖到画布",
  );
  await expect(page.locator(".resource-library > button")).toHaveCount(6);

  await page.locator(".main-agent-fab").click();
  const mainAgentDialog = page.getByRole("dialog", {
    name: "主 Agent 项目协作层",
  });
  await expect(mainAgentDialog).toContainText("没有 DATA / CONTROL 端口");
  await expect(mainAgentDialog).toContainText(
    "不安装或调用执行节点的 Skill/MCP",
  );
  await expect(mainAgentDialog).toContainText("当前未调用模型");
  await page.getByRole("button", { name: "关闭主 Agent 面板" }).click();

  await page.screenshot({
    path: path.join(screenshotDirectory, "prototype-a-studio-1440x900.png"),
    fullPage: false,
  });
  expect(apiRequests).toEqual([]);
});

test("selected direction A provides continuous project, run, data, Agent, domain, and governance views", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/design-preview/prototype?view=project");

  const views = [
    ["项目", "订单与资源协调"],
    ["运行与推演", "运行调查与候选比较"],
    ["数据与知识", "数据与知识"],
    ["Agent 与能力", "Agent 与能力"],
    ["领域", "领域中心"],
    ["治理", "权限与审计"],
  ] as const;

  for (const [navigationLabel, heading] of views) {
    await page
      .locator(".prototype-sidebar")
      .getByRole("button", { name: new RegExp(`^${navigationLabel}`) })
      .click();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBe(0);
  }

  await page
    .locator(".prototype-sidebar")
    .getByRole("button", { name: /^运行与推演/ })
    .click();
  await expect(page.locator(".run-summary")).toContainText(
    "ADVISORY · NOT EXECUTED",
  );
  await expect(page.locator(".candidate-comparison article")).toHaveCount(3);
  await expect(page.locator(".evidence-ledger")).toContainText(
    "Agent / Skill / MCP",
  );
  await page.screenshot({
    path: path.join(screenshotDirectory, "prototype-a-run-1440x900.png"),
    fullPage: false,
  });

  await page
    .locator(".prototype-sidebar")
    .getByRole("button", { name: /^Agent 与能力/ })
    .click();
  await expect(page.locator(".agent-architecture-note")).toContainText(
    "无执行端口",
  );
  await expect(page.locator(".agent-profiles article")).toHaveCount(3);
  await page.screenshot({
    path: path.join(screenshotDirectory, "prototype-a-agents-1440x900.png"),
    fullPage: false,
  });
});

test("selected direction A remains usable at 1280x800 and 476x770", async ({
  page,
}) => {
  for (const viewport of [
    { width: 1280, height: 800, file: "prototype-a-studio-1280x800.png" },
    { width: 476, height: 770, file: "prototype-a-studio-476x770.png" },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/design-preview/prototype?view=studio");

    const layout = await page.evaluate(() => {
      const canvas = document
        .querySelector(".prototype-canvas")
        ?.getBoundingClientRect();
      const nodes = Array.from(
        document.querySelectorAll(".prototype-node"),
      ).map((element) => element.getBoundingClientRect());
      const visibleButtons = Array.from(document.querySelectorAll("button"))
        .map((element) => element.getBoundingClientRect())
        .filter((rect) => rect.width > 0 && rect.height > 0);
      return {
        overflow:
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
        nodeOverlap: nodes.some((first, index) =>
          nodes
            .slice(index + 1)
            .some(
              (second) =>
                !(
                  first.right <= second.left ||
                  first.left >= second.right ||
                  first.bottom <= second.top ||
                  first.top >= second.bottom
                ),
            ),
        ),
        nodeOutsideCanvas: canvas
          ? nodes.some(
              (node) =>
                node.left < canvas.left ||
                node.right > canvas.right ||
                node.top < canvas.top ||
                node.bottom > canvas.bottom,
            )
          : true,
        tinyTouchTargets:
          window.innerWidth <= 520
            ? visibleButtons.filter(
                (rect) => rect.width < 40 || rect.height < 40,
              ).length
            : 0,
      };
    });

    expect(layout.overflow).toBe(0);
    expect(layout.nodeOverlap).toBe(false);
    expect(layout.nodeOutsideCanvas).toBe(false);
    expect(layout.tinyTouchTargets).toBe(0);
    await expect(page.locator(".main-agent-fab")).toBeVisible();
    await page.screenshot({
      path: path.join(screenshotDirectory, viewport.file),
      fullPage: false,
    });
  }
});
