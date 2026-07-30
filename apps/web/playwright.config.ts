import { existsSync } from "node:fs";

import { defineConfig } from "@playwright/test";

const macChrome =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  outputDir: `/tmp/forgeops-playwright-${String(Date.now())}`,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:19802",
    viewport: { width: 1440, height: 960 },
    trace: "off",
    screenshot: "off",
    video: "off",
    launchOptions: existsSync(macChrome) ? { executablePath: macChrome } : {},
  },
  webServer: {
    command: "sh ../../scripts/playwright_servers.sh",
    url: "http://127.0.0.1:19802/health/ready",
    timeout: 30_000,
    reuseExistingServer: false,
  },
});
