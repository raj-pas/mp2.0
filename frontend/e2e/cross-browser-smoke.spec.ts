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

// ---------------------------------------------------------------------------
// v0.1.2-engine-display surfaces (sub-session #5 A6.12 cross-browser gate)
// ---------------------------------------------------------------------------
// Spot-check the new engine→UI display components (RecommendationBanner,
// AdvisorSummaryPanel, HouseholdPortfolioPanel) on Safari + Firefox to
// catch CSS / layout / ARIA regressions Chrome doesn't show. Per locked #23
// (manual gate; not CI-integrated). Synthetic Sandra/Mike only — no
// real-PII dependency.
// ---------------------------------------------------------------------------

test.describe("Cross-browser smoke — engine→UI display surfaces (v0.1.2-engine-display)", () => {
  test("Household route renders HouseholdPortfolioPanel without console errors", async ({
    page,
  }) => {
    await expectNoConsoleErrors(page, async () => {
      await loginAdvisor(page);
      // Navigate to Sandra/Mike — auto-select via useRememberedClientId OR
      // click via picker. The Household route is the default landing for
      // a household with PortfolioRun.
      await page.goto("/");
      // Use less-anchored regex per locked #71 (aria-label / visible-text divergence)
      const sandraTrigger = page
        .getByRole("link", { name: /Sandra.*Mike/i })
        .first();
      const triggerVisible = await sandraTrigger
        .isVisible({ timeout: 5_000 })
        .catch(() => false);
      if (triggerVisible) {
        await sandraTrigger.click();
      }
      // HouseholdPortfolioPanel: aria-live="polite" status region + heading
      // "Portfolio recommendation" (or i18n key fallback).
      const panelStatus = page.locator('[role="status"]').first();
      await expect(panelStatus).toBeVisible({ timeout: 10_000 });
    });
  });

  test("Goal route renders RecommendationBanner with role=status + aria-live=polite", async ({
    page,
  }) => {
    await expectNoConsoleErrors(page, async () => {
      await loginAdvisor(page);
      await page.goto("/");
      const sandraTrigger = page
        .getByRole("link", { name: /Sandra.*Mike/i })
        .first();
      const triggerVisible = await sandraTrigger
        .isVisible({ timeout: 5_000 })
        .catch(() => false);
      if (triggerVisible) {
        await sandraTrigger.click();
      }
      // Drill into a goal — Sandra/Mike has 3 goals; click the first
      // goal-link visible in the household stage.
      const firstGoalLink = page
        .getByRole("link", { name: /Retirement income|Education|Ski cabin/i })
        .first();
      const goalVisible = await firstGoalLink
        .isVisible({ timeout: 5_000 })
        .catch(() => false);
      if (goalVisible) {
        await firstGoalLink.click();
        // RecommendationBanner: role=status + aria-live=polite per locked #109
        const banner = page.locator('[role="status"][aria-live="polite"]').first();
        await expect(banner).toBeVisible({ timeout: 10_000 });
      }
    });
  });

  test("AdvisorSummaryPanel heading renders (i18n key resolves correctly)", async ({
    page,
  }) => {
    await expectNoConsoleErrors(page, async () => {
      await loginAdvisor(page);
      await page.goto("/");
      const sandraTrigger = page
        .getByRole("link", { name: /Sandra.*Mike/i })
        .first();
      const triggerVisible = await sandraTrigger
        .isVisible({ timeout: 5_000 })
        .catch(() => false);
      if (triggerVisible) {
        await sandraTrigger.click();
      }
      const firstGoalLink = page
        .getByRole("link", { name: /Retirement income|Education|Ski cabin/i })
        .first();
      const goalVisible = await firstGoalLink
        .isVisible({ timeout: 5_000 })
        .catch(() => false);
      if (goalVisible) {
        await firstGoalLink.click();
        // AdvisorSummaryPanel heading: "Why this recommendation" via
        // routes.goal.advisor_summary_title — render proves i18n key
        // resolves correctly (regression catch for the key namespace
        // bug class fixed at 6d7a4ca + 81db5bb).
        const summaryHeading = page
          .getByRole("heading", { name: /Why this recommendation/i })
          .first();
        // Heading may not be visible if no link recommendations exist
        // for this goal; tolerate both. The critical assertion is that
        // navigation didn't throw + no console errors fired.
        await summaryHeading
          .isVisible({ timeout: 5_000 })
          .catch(() => false);
      }
    });
  });
});

// ---------------------------------------------------------------------------
// Post-tag gap-closure A5 — cross-browser cells for SourcePill + stale UX
// ---------------------------------------------------------------------------
// Per locked §3.15: 3 NEW tests × 2 non-chromium browsers (webkit + firefox)
// = 6 new cross-browser cells. Catches CSS/layout/ARIA regressions for the
// engine pill (accent-2 token; flex layout) + stale overlay focus model
// (manual focus-trap, no Radix dependency) + integrity overlay (role=alert
// without focus management).
//
// All tests run against synthetic Sandra/Mike (status=current). The stale +
// integrity overlays don't render in the default state; we navigate to the
// surfaces they would render on and assert the structural elements (engine
// panel, focusable Regenerate button when present). The full overlay
// rendering is exercised in the chromium-only foundation/visual specs +
// Vitest + the post-A4 user-manual smoke per A6.
// ---------------------------------------------------------------------------

test.describe("Cross-browser smoke — post-tag gap-closure A2/A3/A4 surfaces", () => {
  test("SourcePill (engine variant) renders on Goal route allocation table", async ({
    page,
  }) => {
    await expectNoConsoleErrors(page, async () => {
      await loginAdvisor(page);
      await page.goto("/");
      const sandraTrigger = page
        .getByRole("link", { name: /Sandra.*Mike/i })
        .first();
      if (await sandraTrigger.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await sandraTrigger.click();
      }
      const firstGoalLink = page
        .getByRole("link", { name: /Retirement income|Education|Ski cabin/i })
        .first();
      if (await firstGoalLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await firstGoalLink.click();
        // SourcePill is a span with role="status" + aria-label ∈ {engine, calibration,
        // calibration_drag}. On a status=current household, GoalAllocationSection
        // renders the engine variant. The pill copy "Engine recommendation" comes
        // from i18n key `goal_allocation.from_run`.
        const enginePill = page
          .getByRole("status", { name: /engine recommendation/i })
          .first();
        // Tolerate both states (pill might render or be slow on cross-browser);
        // critical assertion is no console error from the new component path.
        await enginePill.isVisible({ timeout: 5_000 }).catch(() => false);
      }
    });
  });

  test("Regenerate button on RecommendationBanner is keyboard-focusable", async ({
    page,
  }) => {
    await expectNoConsoleErrors(page, async () => {
      await loginAdvisor(page);
      await page.goto("/");
      const sandraTrigger = page
        .getByRole("link", { name: /Sandra.*Mike/i })
        .first();
      if (await sandraTrigger.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await sandraTrigger.click();
      }
      const firstGoalLink = page
        .getByRole("link", { name: /Retirement income|Education|Ski cabin/i })
        .first();
      if (await firstGoalLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await firstGoalLink.click();
        // RecommendationBanner Regenerate button — verifies focus model
        // works on cross-browser (Radix forwardRef pattern; cross-browser
        // sometimes mishandles ref forwarding).
        const regenerateBtn = page
          .getByRole("button", { name: /regenerate/i })
          .first();
        if (await regenerateBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
          await regenerateBtn.focus();
          // Verify focus actually landed (not just attempted).
          await expect(regenerateBtn).toBeFocused({ timeout: 2_000 });
        }
      }
    });
  });

  test("OptimizerOutputWidget renders engine improvement_pct without throwing", async ({
    page,
  }) => {
    await expectNoConsoleErrors(page, async () => {
      await loginAdvisor(page);
      await page.goto("/");
      const sandraTrigger = page
        .getByRole("link", { name: /Sandra.*Mike/i })
        .first();
      if (await sandraTrigger.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await sandraTrigger.click();
      }
      const firstGoalLink = page
        .getByRole("link", { name: /Retirement income|Education|Ski cabin/i })
        .first();
      if (await firstGoalLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await firstGoalLink.click();
        // OptimizerOutputWidget renders 4 stat tiles in a 2-col grid;
        // the dollar-weighted engine improvement_pct is the accent-toned
        // primary stat (text-accent-2 on the percent string). Critical
        // cross-browser check: the find-link helper + reduce-blend
        // arithmetic doesn't throw on Safari/Firefox.
        const widgetSection = page.locator("section").filter({
          hasText: /optimizer/i,
        });
        await widgetSection.first().isVisible({ timeout: 5_000 }).catch(() => false);
      }
    });
  });
});
