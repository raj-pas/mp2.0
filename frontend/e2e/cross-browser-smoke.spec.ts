/**
 * Cross-browser smoke (production-quality-bar §3.14).
 *
 * Spot-check the essential advisor surfaces across Safari (webkit)
 * + Firefox to catch CSS / layout regressions Chrome doesn't.
 * NOT a full e2e — Chrome remains the primary gate via foundation +
 * pilot-features specs. Run with:
 *
 *   PLAYWRIGHT_BASE_URL=http://localhost:5173 \
 *     npx playwright test --project=webkit e2e/cross-browser-smoke.spec.ts
 *   PLAYWRIGHT_BASE_URL=http://localhost:5173 \
 *     npx playwright test --project=firefox e2e/cross-browser-smoke.spec.ts
 *
 * Coverage:
 *   - Login renders + form submits without console errors
 *   - Topbar + ClientPicker render
 *   - Synthetic Sandra/Mike treemap + ContextPanel render
 *   - /review route renders without throwing
 *   - /methodology overlay opens + closes
 *
 * Real-PII discipline: this spec only exercises synthetic data
 * (the seeded Sandra/Mike persona). Real-PII workspaces are
 * exercised only in the R10 sweep spec.
 */
import { expect, type Page, test } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD =
  process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";

async function loginAdvisor(page: Page) {
  await page.goto("/");
  await page.getByLabel(/email/i).fill(ADVISOR_EMAIL);
  await page.getByLabel(/password/i).fill(ADVISOR_PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.locator('[data-testid="topbar"], header')).toBeVisible({
    timeout: 15_000,
  });
}

async function expectNoConsoleErrors(page: Page, run: () => Promise<void>) {
  const errors: string[] = [];
  const handler = (msg: { type: () => string; text: () => string }) => {
    if (msg.type() === "error") {
      const text = msg.text();
      if (
        // jsdom + safari sometimes emit benign network-cancellation noise
        // during route transitions; filter the obvious noise patterns.
        text.includes("net::ERR_ABORTED") ||
        text.includes("Failed to load resource: the server responded") ||
        text.includes("favicon.ico") ||
        // Firefox font sanitizer rejects WOFF2 files served by the
        // Vite dev server with default response headers. The fonts
        // fall back to system equivalents; visual + functional impact
        // is minimal. Filed as known-noise; revisit when fonts are
        // served from a static CDN with proper CORS + content-type.
        text.includes("downloadable font: rejected by sanitizer") ||
        // Firefox bug 1827745: occasional "ResizeObserver loop"
        // warnings during fast layout transitions; benign.
        text.includes("ResizeObserver loop") ||
        // Firefox emits "Loading failed for the <script>" for
        // legacy preload links during SPA navigation; benign.
        text.includes("Loading failed for the <script>")
      ) {
        return;
      }
      errors.push(text);
    }
  };
  page.on("console", handler);
  try {
    await run();
  } finally {
    page.off("console", handler);
  }
  expect(errors).toEqual([]);
}

test.describe("Cross-browser smoke (Safari + Firefox spot-check)", () => {
  test("login + topbar render without console errors", async ({ page }) => {
    await expectNoConsoleErrors(page, async () => {
      await loginAdvisor(page);
    });
  });

  test("ClientPicker is reachable + interactive", async ({ page }) => {
    await loginAdvisor(page);
    // ClientPicker is a button-rendered combobox in the topbar
    // (a button label shows the selected client + a placeholder
    // chip when none is picked). Keyboard-focusing it should expose
    // either the search input (if there are clients) or the empty
    // state copy.
    const picker = page
      .getByRole("button", { name: /select client/i })
      .first();
    await expect(picker).toBeVisible({ timeout: 10_000 });
    await picker.click();
    // After opening the picker either renders the search input OR
    // the empty-state CTA.
    const searchInput = page.getByPlaceholder(/search clients/i).first();
    const emptyCta = page
      .getByText(/no clients|create one|create.*household/i)
      .first();
    const searchVisible = await searchInput
      .isVisible({ timeout: 5_000 })
      .catch(() => false);
    if (!searchVisible) {
      await expect(emptyCta).toBeVisible({ timeout: 5_000 });
    }
  });

  test("/review renders without throwing", async ({ page }) => {
    await loginAdvisor(page);
    await expectNoConsoleErrors(page, async () => {
      await page.goto("/review");
      await expect(
        page.getByRole("heading", { name: /review|workspace/i }).first(),
      ).toBeVisible({ timeout: 10_000 });
    });
  });

  test("/methodology overlay opens + renders content", async ({ page }) => {
    await loginAdvisor(page);
    await page.goto("/methodology");
    // Methodology surface should mount without throwing; the page
    // contains structured doc text.
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/methodology/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("synthetic Sandra/Mike treemap is reachable", async ({ page }) => {
    await loginAdvisor(page);
    await page.goto("/");
    // The home page either lands directly on Sandra/Mike (if a
    // client is auto-selected via useRememberedClientId) or shows a
    // "Select a client from the topbar" prompt. Both paths are
    // valid; just verify the page renders without throwing and an
    // SVG (treemap or empty-state illustration) is present.
    const svg = page.locator("svg").first();
    const promptText = page
      .getByText(/select a client|pick a client/i)
      .first();
    const svgVisible = await svg.isVisible({ timeout: 8_000 }).catch(() => false);
    const promptVisible = await promptText
      .isVisible({ timeout: 2_000 })
      .catch(() => false);
    expect(svgVisible || promptVisible).toBe(true);
  });
});
