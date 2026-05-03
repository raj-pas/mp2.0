import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR ?? "test-results",
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    // Cross-browser spot-check (production-quality-bar §3.14). Run
    // targeted smoke specs against Safari + Firefox to catch CSS /
    // layout regressions Chrome doesn't surface. Full e2e coverage
    // on Chrome remains the primary gate. Examples:
    //   npx playwright test --project=webkit e2e/cross-browser-smoke.spec.ts
    //   npx playwright test --project=firefox e2e/cross-browser-smoke.spec.ts
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
  ],
});
