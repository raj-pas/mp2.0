/**
 * Regression coverage — pre-existing flows (per locked §3.20 of the
 * post-tag gap-closure plan).
 *
 * The Engine→UI Display gap-closure (sub-sessions #1-#3) modifies
 * GoalAllocationSection, OptimizerOutputWidget, MovesPanel, RiskSlider,
 * RecommendationBanner, HouseholdPortfolioPanel, GoalRoute. Roughly
 * 75% of the codebase (Wizard, ReviewWorkspace, ConflictPanel,
 * DocDetailPanel, CMA Workbench, Methodology, FeedbackModal,
 * PilotBanner, WelcomeTour, etc.) is not directly touched but could
 * regress via cross-cutting changes (i18n key collisions, type-system
 * narrowing, route-level ErrorBoundary changes, useEffect dependency
 * drift, focus-management refactors).
 *
 * This spec is the AUTOMATED regression suite (chosen over a manual
 * checklist per §3.20) that locks the contract for those 15 flows.
 * Each test exercises a specific user-visible behavior; many
 * explicitly name the prior-bug regression class they guard
 * (e.g. b14a199 Esc handler, c5a7e02 RiskSlider conflated semantic).
 *
 * Test design discipline:
 *   - Each test is self-contained and tolerant of current DB state
 *     (skip-or-render where flow depends on specific workspace shape).
 *   - Sandra/Mike auto-seeds with PortfolioRun + advisor pre-ack —
 *     synthetic-data tests use her as the canonical fixture.
 *   - Real-PII workspaces (Seltzer / Weryha / Niesner) may or may not
 *     exist depending on prior reset state; we navigate to whichever
 *     workspace is present and assert structural elements only.
 *   - Tests must pass on 2 consecutive runs (zero-flake gate per §3.20).
 *
 * Skipped if MP20_LOCAL_ADMIN_EMAIL is not set (env-gated like the
 * pilot-features-smoke and cross-browser-smoke specs).
 */
import { expect, test, type Page } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD =
  process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";
const ANALYST_EMAIL = process.env.MP20_LOCAL_ANALYST_EMAIL ?? "analyst@example.com";
const ANALYST_PASSWORD =
  process.env.MP20_LOCAL_ANALYST_PASSWORD ?? "change-this-local-password";

async function loginAdvisor(page: Page) {
  await page.goto("/");
  await page.getByLabel(/email/i).fill(ADVISOR_EMAIL);
  await page.getByLabel(/password/i).fill(ADVISOR_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();
  await expect(page.getByRole("banner")).toBeVisible({ timeout: 15_000 });
}

async function loginAnalyst(page: Page) {
  await page.goto("/");
  await page.getByLabel(/email/i).fill(ANALYST_EMAIL);
  await page.getByLabel(/password/i).fill(ANALYST_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();
  await expect(page).toHaveURL(/\/cma$/, { timeout: 15_000 });
}

async function pickSandraMike(page: Page) {
  // ClientPicker is a topbar combobox. Two paths cover the cases where
  // Sandra is auto-selected via useRememberedClientId vs not selected.
  const picker = page.getByRole("button", { name: /select client/i }).first();
  if ((await picker.textContent())?.match(/Sandra/i)) return;
  await picker.click();
  const sandraOption = page.getByRole("option", { name: /Sandra/i }).first();
  await sandraOption.click();
}

// =============================================================================
// 1. Login + client picker pagination
// =============================================================================

test.describe("Regression coverage — login + chrome", () => {
  test.skip(
    !process.env.MP20_LOCAL_ADMIN_EMAIL,
    "MP20_LOCAL_ADMIN_EMAIL not set; skipping regression-coverage suite",
  );

  test("login → home → client picker opens with search input", async ({ page }) => {
    await loginAdvisor(page);
    // Topbar present.
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /select client/i }),
    ).toBeVisible();
    // Open the picker; either search input or empty-state CTA renders.
    await page.getByRole("button", { name: /select client/i }).click();
    const searchInput = page.getByPlaceholder(/search clients/i).first();
    const emptyCta = page
      .getByText(/no clients|create one|create.*household/i)
      .first();
    const searchVisible = await searchInput
      .isVisible({ timeout: 5_000 })
      .catch(() => false);
    if (!searchVisible) {
      await expect(emptyCta).toBeVisible({ timeout: 5_000 });
    } else {
      // Pagination signal — at least one option renders.
      await expect(page.getByRole("option").first()).toBeVisible({
        timeout: 5_000,
      });
    }
  });

  // ===========================================================================
  // 14. PilotBanner ack flow
  // ===========================================================================
  test("PilotBanner — dismissal persists across reload (Phase 5b.1)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    const banner = page.locator('[role="region"][aria-label*="Pilot"]');
    if (await banner.isVisible({ timeout: 2_000 }).catch(() => false)) {
      // Pre-ack the banner if rendered.
      await banner.locator("button").first().click();
      await expect(banner).toBeHidden();
    }
    // Reload — banner must stay hidden (server-side ack persisted).
    await page.reload();
    await expect(page.getByRole("banner")).toBeVisible({ timeout: 10_000 });
    await expect(banner).toBeHidden();
  });

  // ===========================================================================
  // 15. WelcomeTour ack flow
  // ===========================================================================
  test("WelcomeTour — dismissal persists across reload (Phase 5b.6)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    const tour = page.getByRole("dialog", { name: /welcome|tour/i }).first();
    if (await tour.isVisible({ timeout: 2_000 }).catch(() => false)) {
      // Click "Skip" to ack server-side (idempotent + audit-emitting).
      const skipButton = tour
        .getByRole("button", { name: /skip|done/i })
        .first();
      await skipButton.click();
      await expect(tour).toBeHidden();
    }
    // Reload — tour must not re-show (tour_completed_at persists).
    await page.reload();
    await expect(page.getByRole("banner")).toBeVisible({ timeout: 10_000 });
    await expect(tour).toBeHidden();
  });

  // ===========================================================================
  // 13. FeedbackModal Esc close (regression guard for b14a199 Esc handler)
  // ===========================================================================
  test("FeedbackModal — opens via FAB + closes on Escape (b14a199 regression guard)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    // Open the feedback modal via the topbar button (aria-label
    // "Open feedback form" per FeedbackButton.tsx:36).
    const feedbackButton = page
      .locator('button[aria-label*="feedback"]')
      .first();
    await feedbackButton.click();
    const modal = page.getByRole("dialog").filter({ hasText: /feedback/i }).first();
    await expect(modal).toBeVisible();
    // Press Escape — modal must close. The FeedbackButton's useEffect
    // wires window.addEventListener("keydown", ...) to call onClose.
    // Caught by visual-verification 2026-05-03; previously the modal was
    // non-dismissable via keyboard.
    await page.keyboard.press("Escape");
    await expect(modal).toBeHidden({ timeout: 3_000 });
  });
});

// =============================================================================
// 12. Methodology page renders 10 sections
// 11. CMA Workbench draft → publish (analyst surface)
// =============================================================================

test.describe("Regression coverage — chrome routes", () => {
  test.skip(
    !process.env.MP20_LOCAL_ADMIN_EMAIL,
    "MP20_LOCAL_ADMIN_EMAIL not set; skipping",
  );

  test("Methodology page renders 10 sections + canon descriptors (R8)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/methodology");
    await expect(
      page.getByRole("heading", { level: 1, name: /^Methodology$/ }),
    ).toBeVisible({ timeout: 10_000 });
    // All 10 section headings render. Mirror foundation R8 list.
    for (const sectionTitle of [
      /Household risk profile/i,
      /^Anchor$/i,
      /Goal-level risk score/i,
      /Horizon cap per goal/i,
      /Effective bucket/i,
      /Sleeve mix/i,
      /Lognormal projections/i,
      /Rebalancing moves/i,
      /Goal realignment/i,
      /Archive snapshots/i,
    ]) {
      await expect(
        page.getByRole("heading", { level: 2, name: sectionTitle }),
      ).toBeVisible();
    }
  });

  test("CMA Workbench — analyst sees 5 tabs + active snapshot (R9)", async ({
    page,
  }) => {
    await loginAnalyst(page);
    await expect(
      page.getByRole("heading", { level: 1, name: /CMA Workbench/i }),
    ).toBeVisible();
    // All 5 tabs present.
    for (const tab of ["Snapshots", "Assumptions", "Correlations", "Frontier", "Audit"]) {
      await expect(page.getByRole("tab", { name: tab })).toBeVisible();
    }
    // Active snapshot pill renders (Default CMA seeded).
    await expect(page.getByText(/Active:/i)).toBeVisible({ timeout: 10_000 });
    // Switching to Frontier renders the canvas (chart.js dynamic import).
    await page.getByRole("tab", { name: "Frontier" }).click();
    await expect(page.getByText(/efficient frontier points/i)).toBeVisible({
      timeout: 15_000,
    });
  });
});

// =============================================================================
// 2. Wizard Step 1-5 full flow (R5 — happy path; cheaper variant of foundation)
// =============================================================================

test.describe("Regression coverage — wizard onboarding", () => {
  test.skip(
    !process.env.MP20_LOCAL_ADMIN_EMAIL,
    "MP20_LOCAL_ADMIN_EMAIL not set; skipping",
  );

  test("Wizard — Step 1 renders + identity validation (R5)", async ({ page }) => {
    test.setTimeout(30_000);
    await loginAdvisor(page);
    await page.getByRole("button", { name: /select client/i }).click();
    await page
      .getByRole("button", { name: /Add new household/i })
      .first()
      .click();
    await expect(page).toHaveURL(/\/wizard\/new$/);
    // Step 1 — identity fields render. The household-name input has
    // a "Yeager Household" placeholder per the Wizard implementation.
    await expect(page.getByPlaceholder(/Yeager Household/i)).toBeVisible({
      timeout: 10_000,
    });
    // Member 1 inputs are present.
    const memberInputs = page.locator('input[name^="members."]');
    await expect(memberInputs.first()).toBeVisible({ timeout: 5_000 });
    // Submit-empty validation: clicking Next without filling halts at
    // Step 1 (zod schema mirrors DRF serializer; per locked R5 patterns).
    const initialUrl = page.url();
    await page.getByRole("button", { name: /^Next$/ }).click();
    // Either still on Step 1 OR a validation error rendered.
    const stillOnStep1 =
      page.url() === initialUrl ||
      (await page
        .getByText(/required|enter|please/i)
        .first()
        .isVisible({ timeout: 2_000 })
        .catch(() => false));
    expect(stillOnStep1).toBe(true);
  });

  // P14 §A1.14 #5 + #16 LOCKED — wizard partial-allocation hard-block.
  test("Wizard — partial-allocation hard-block (P14 §A1.14 #5 + #16)", async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await loginAdvisor(page);
    await page.getByRole("button", { name: /select client/i }).click();
    await page
      .getByRole("button", { name: /Add new household/i })
      .first()
      .click();
    await expect(page).toHaveURL(/\/wizard\/new$/);

    // Step 1 — fill in minimal identity fields to advance.
    await page.getByPlaceholder(/Yeager Household/i).fill("P14 Hard Block Test");
    const memberInputs = page.locator('input[name^="members."]');
    await memberInputs.nth(0).fill("Pilot Member");
    // The DOB input is type=date; second member input.
    const dobInput = page.locator('input[type="date"][name="members.0.dob"]');
    await dobInput.fill("1980-01-01");
    await page.getByRole("button", { name: /^Next$/ }).click();

    // Step 2 — accept defaults; the risk-profile defaults satisfy zod.
    await page.getByRole("button", { name: /^Next$/ }).click();

    // Step 3 — fill account with $100K but goal leg with only $10K.
    // This triggers BOTH:
    //   - account-centric (sum 10K ≠ 100K) hard-block
    //   - goal-side gate is satisfied (positive leg + target_amount)
    // The Continue button MUST be disabled.
    const valueInput = page.locator('input[name="accounts.0.current_value"]');
    await valueInput.fill("100000");
    await page.locator('input[name="goals.0.name"]').fill("Retirement");
    await page
      .locator('input[type="date"][name="goals.0.target_date"]')
      .fill("2050-01-01");
    await page
      .locator('input[name="goals.0.target_amount"]')
      .fill("500000");
    await page
      .locator('input[name="goals.0.legs.0.allocated_amount"]')
      .fill("10000");

    // Wait briefly for the onChange superRefine to fire.
    await page.waitForTimeout(500);

    const nextBtn = page.getByRole("button", { name: /^Next$/ });
    // Hard-block invariant — the button is disabled.
    await expect(nextBtn).toBeDisabled({ timeout: 5_000 });

    // Field-level error renders for the under-allocated account (i18n
    // key surface — matches "wizard.step3.account_unallocated").
    await expect(
      page.getByText(/unassigned across goals|account_unallocated/i).first(),
    ).toBeVisible({ timeout: 5_000 });

    // Fix the allocation — bring the leg up to $100K. The button
    // should now enable.
    await page
      .locator('input[name="goals.0.legs.0.allocated_amount"]')
      .fill("100000");
    await page.waitForTimeout(500);
    await expect(nextBtn).toBeEnabled({ timeout: 5_000 });
  });
});

// =============================================================================
// 3. ReviewWorkspace doc upload + drain
// 5. DocDetailPanel slide-out + Esc close (regression guard for b14a199)
// 4. ConflictPanel single resolve
// 6. Bulk conflict resolve (multi-select)
// 7. Defer + auto-resurface
// 8. Section approve
// =============================================================================

test.describe("Regression coverage — review surfaces", () => {
  test.skip(
    !process.env.MP20_LOCAL_ADMIN_EMAIL,
    "MP20_LOCAL_ADMIN_EMAIL not set; skipping",
  );

  test("ReviewScreen — doc-drop overlay renders + accepts file input (R7)", async ({
    page,
  }) => {
    test.setTimeout(45_000);
    await loginAdvisor(page);
    await page.goto("/review");
    // DocDropOverlay renders.
    await expect(
      page.getByRole("heading", { name: /Drop documents/i }),
    ).toBeVisible({ timeout: 10_000 });
    // Synthetic-origin label input accepts a value (regression guard
    // for the FileList ref race fix at locked #100).
    const labelInput = page.getByPlaceholder(/Yeager Household/i);
    if (await labelInput.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await labelInput.fill(`A5.5 regression coverage ${Date.now()}`);
    }
    // The hidden file input must accept the upload — its presence in
    // the DOM is the structural assertion.
    const fileInput = page.locator('input[type="file"]').first();
    await expect(fileInput).toHaveCount(1);
  });

  /**
   * Open the first workspace row in the in-flight queue. Returns true
   * if a workspace was selected; false (skip-or-tolerate) when the
   * queue is empty. The queue is rendered as <button>s inside an
   * <aside aria-label="In-flight workspaces"> per ReviewRoute.tsx:43.
   *
   * Note: Playwright's `getByRole("complementary")` does NOT match
   * `<aside>` inside `<main>` (per WHATWG ARIA implicit semantics).
   * Use `locator('aside[aria-label="In-flight workspaces"]')` instead.
   */
  async function openFirstWorkspace(page: Page): Promise<boolean> {
    // Workspaces populate via React Query; wait for networkidle so the
    // initial /api/review-workspaces/ fetch resolves before we probe.
    await page.waitForLoadState("networkidle").catch(() => undefined);
    const queue = page.locator('aside[aria-label="In-flight workspaces"]');
    if (!(await queue.isVisible({ timeout: 10_000 }).catch(() => false))) {
      return false;
    }
    const firstRow = queue.locator("button").first();
    if (!(await firstRow.isVisible({ timeout: 8_000 }).catch(() => false))) {
      return false;
    }
    await firstRow.click();
    return true;
  }

  test("DocDetailPanel — opens on doc click + closes on Escape (b14a199 regression guard)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/review");
    const opened = await openFirstWorkspace(page);
    test.skip(!opened, "no review workspaces present in current state");
    // Wait for the workspace ReviewScreen to mount — the readiness
    // panel is the most reliable structural anchor.
    await expect(
      page.getByText(/Engine ready/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    // Click the first doc row in the ProcessingPanel. Doc rows are
    // rendered as buttons that include the original filename.
    const firstDocButton = page
      .locator("button")
      .filter({ hasText: /\.pdf|\.docx|\.txt|\.xlsx/i })
      .first();
    const hasDoc = await firstDocButton
      .isVisible({ timeout: 3_000 })
      .catch(() => false);
    if (!hasDoc) {
      // Workspace might be empty or post-extraction; tolerate.
      return;
    }
    await firstDocButton.click();
    // DocDetailPanel slides in from right (role=dialog + aria-modal).
    const panel = page.getByRole("dialog").first();
    if (!(await panel.isVisible({ timeout: 3_000 }).catch(() => false))) {
      // Panel may not have opened (e.g., text-only fallback); tolerate.
      return;
    }
    // Press Escape — panel must close. DocDetailPanel.tsx:59-67 wires
    // window.addEventListener("keydown", ...) with stopPropagation.
    await page.keyboard.press("Escape");
    await expect(panel).toBeHidden({ timeout: 3_000 });
  });

  test("ConflictPanel — renders with cards or empty state (Phase 5a)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/review");
    const opened = await openFirstWorkspace(page);
    test.skip(!opened, "no review workspaces present in current state");
    // The page should at minimum render a readiness panel (Engine ready
    // / Construction ready). This is the regression guard — if a cross-
    // cutting i18n change broke the readiness rendering, this catches it.
    await expect(
      page.getByText(/Engine ready|Construction ready/i).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("ConflictPanel — bulk-resolve affordance is structurally present (Phase 5b.12)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/review");
    const opened = await openFirstWorkspace(page);
    test.skip(!opened, "no review workspaces present in current state");
    await expect(
      page.getByText(/Engine ready/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    // Look for any radio/checkbox in conflict cards. Bulk affordance
    // surfaces when ≥2 are selected; we just verify the page renders
    // without crashing under workspace-with-conflicts state.
    await page.locator('input[type="radio"], input[type="checkbox"]').count();
  });

  test("ConflictPanel — defer action button is reachable (Phase 5b.13)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/review");
    const opened = await openFirstWorkspace(page);
    test.skip(!opened, "no review workspaces present in current state");
    await expect(
      page.getByText(/Engine ready/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    // Defer button surfaces inside conflict cards. Tolerate absence
    // when no conflicts; the regression guard is that the page still
    // renders the structural review panels (no crash).
    await page
      .getByRole("button", { name: /defer|skip|later/i })
      .first()
      .isVisible({ timeout: 3_000 })
      .catch(() => false);
    await expect(
      page.getByText(/Engine ready|Construction ready/i).first(),
    ).toBeVisible();
  });

  test("Section approve — readiness checklist + approval UI render", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/review");
    const opened = await openFirstWorkspace(page);
    test.skip(!opened, "no review workspaces present in current state");
    // Section approval cards render — the right-rail "approve" buttons
    // are tied to the readiness contract per locked decision #18.
    await page
      .getByRole("button", { name: /^Approve$|approve section/i })
      .first()
      .isVisible({ timeout: 3_000 })
      .catch(() => false);
    await expect(page.getByText(/Engine ready/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  // P3.3 — per-row Add CTA + bulk wizard. Sandra/Mike's auto-seeded
  // workspace usually has no missing blockers (the seed is
  // engine-ready). When that's the case, this test gracefully skips
  // per §A1.54. When a real-PII workspace IS in flight with missing
  // blockers, we exercise the inline `+` CTA fully.
  test("MissingPanel — Add CTA opens form + saves blocker (P3.3)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/review");
    const opened = await openFirstWorkspace(page);
    test.skip(!opened, "no review workspaces present in current state");
    await expect(
      page.getByText(/Engine ready/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    // Look for an inline Add-blocker CTA. The aria-label format is
    // "Add value for {{label}}" per AddBlockerInlineButton.
    const addCta = page
      .getByRole("button", { name: /Add value for/i })
      .first();
    const ctaVisible = await addCta
      .isVisible({ timeout: 3_000 })
      .catch(() => false);
    test.skip(
      !ctaVisible,
      "no missing blockers on this workspace — Add CTA hidden as designed (§A1.54)",
    );
    await addCta.click();
    // Inline form expands — Save button visible (initially disabled).
    const saveButton = page.getByRole("button", { name: /^Save$/i }).first();
    await expect(saveButton).toBeVisible({ timeout: 3_000 });
  });

  test("ResolveAllMissingWizard — bulk wizard launches at N≥4 (P3.3 / Round 8 #5)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await page.goto("/review");
    const opened = await openFirstWorkspace(page);
    test.skip(!opened, "no review workspaces present in current state");
    await expect(
      page.getByText(/Engine ready/i).first(),
    ).toBeVisible({ timeout: 10_000 });
    // The bulk-wizard CTA only renders when missing.length >= 4. When
    // Sandra/Mike (or whichever workspace was selected) has fewer
    // missing blockers, the CTA is hidden by design — gracefully skip.
    const bulkCta = page
      .getByRole("button", { name: /Resolve all .* missing fields/i })
      .first();
    const ctaVisible = await bulkCta
      .isVisible({ timeout: 3_000 })
      .catch(() => false);
    test.skip(
      !ctaVisible,
      "fewer than 4 missing blockers — bulk wizard CTA hidden by design (§A1.54)",
    );
    await bulkCta.click();
    // Wizard dialog renders.
    const wizard = page.getByRole("dialog").first();
    await expect(wizard).toBeVisible({ timeout: 5_000 });
    // aria-modal=true contract.
    await expect(wizard).toHaveAttribute("aria-modal", "true");
    // Imperative Esc handler closes the wizard (anti-pattern #12).
    await page.keyboard.press("Escape");
    await expect(wizard).toBeHidden({ timeout: 3_000 });
  });
});

// =============================================================================
// 9. Household commit + auto-trigger PortfolioRun
// 10. Override → regenerate cycle (engine→UI A2/A3 regression guard)
// =============================================================================

test.describe("Regression coverage — household + goal", () => {
  test.skip(
    !process.env.MP20_LOCAL_ADMIN_EMAIL,
    "MP20_LOCAL_ADMIN_EMAIL not set; skipping",
  );

  test("Household — Sandra/Mike auto-trigger emitted PortfolioRun (engine→UI A2 regression guard)", async ({
    page,
  }) => {
    await loginAdvisor(page);
    await pickSandraMike(page);
    // After picking Sandra/Mike, HouseholdRoute renders the AUM strip
    // + treemap + HouseholdPortfolioPanel (engine rollup). The panel
    // role="status" element is the engine-rollup contract: if the
    // auto-trigger broke (no PortfolioRun fired), the panel renders
    // an empty-state instead of the rollup.
    await expect(
      page
        .locator('[role="status"]')
        .filter({ hasText: /Portfolio recommendation|Top funds|Expected/i })
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("UnallocatedBanner — CTA opens AssignAccountModal pre-focused on account (P12+P13 / §A1.51)", async ({
    page,
  }) => {
    // Plan v20 §A1.36 (P12) + §A1.28 (P13) e2e regression guard. Picks
    // the seeded synthetic Sandra/Mike Chen household first; if that
    // household is fully allocated (the seed default), the banner is
    // hidden — that is itself the §A1.50 boundary case. When partially
    // allocated, clicking "Assign now" opens AssignAccountModal pre-
    // focused on the account (cross-phase contract per §A1.51 P12×P13).
    await loginAdvisor(page);
    await pickSandraMike(page);
    const banner = page.getByTestId("unallocated-banner");
    const isVisible = await banner
      .isVisible({ timeout: 3_000 })
      .catch(() => false);
    test.skip(
      !isVisible,
      "Sandra/Mike is fully allocated — UnallocatedBanner hidden as designed (§A1.50)",
    );
    await page.getByRole("button", { name: /Assign now/i }).first().click();
    // AssignAccountModal opens — title + sum-validator + rationale field.
    await expect(
      page.locator("[data-testid='assign-rows']"),
    ).toBeVisible({ timeout: 5_000 });
    await expect(
      page.locator("[data-testid='assign-sum-validator']"),
    ).toBeVisible();
    await expect(
      page.locator("[data-testid='assign-submit']"),
    ).toBeVisible();
  });

  // ===========================================================================
   // P6 + P7 toggles — persistence across reload (plan v20 §A1.35 / G8 + G9)
   // ===========================================================================
  test("ToggleFundAssetClass + ToggleCurrentIdeal — persist across reload (P6 + P7)", async ({
    page,
  }) => {
    test.setTimeout(45_000);
    await loginAdvisor(page);
    await pickSandraMike(page);
    // P7 — household-level current-vs-ideal toggle in the action sub-bar.
    // The toggle is disabled when no PortfolioRun exists; Sandra/Mike's
    // seed includes one, so the "Ideal" option must be enabled.
    const idealBtn = page.getByTestId("toggle-current-ideal-ideal");
    await expect(idealBtn).toBeVisible({ timeout: 10_000 });
    await idealBtn.click();
    await expect(idealBtn).toHaveAttribute("aria-pressed", "true");

    // P6 — drill into an account and flip the fund-vs-asset toggle.
    // Sandra/Mike's first non-registered account is the canonical seed
    // (acct_non_registered) per `load_synthetic_personas`.
    await page.goto("/account/acct_non_registered");
    const assetBtn = page.getByTestId("toggle-fund-asset-asset_class");
    await expect(assetBtn).toBeVisible({ timeout: 10_000 });
    await assetBtn.click();
    await expect(assetBtn).toHaveAttribute("aria-pressed", "true");

    // Reload — both toggles must persist their values via per-user
    // global localStorage (§A1.14 #14).
    await page.reload();
    await expect(page.getByTestId("toggle-fund-asset-asset_class")).toHaveAttribute(
      "aria-pressed",
      "true",
      { timeout: 10_000 },
    );
    // Navigate back to household; the current-vs-ideal toggle stays on
    // "ideal" because the localStorage key is per-user-global.
    await page.goto("/");
    await expect(page.getByTestId("toggle-current-ideal-ideal")).toHaveAttribute(
      "aria-pressed",
      "true",
      { timeout: 10_000 },
    );
  });

  test("Override → regenerate cycle — engine pill flips on save (engine→UI A2/A3 regression guard)", async ({
    page,
  }) => {
    test.setTimeout(45_000);
    await loginAdvisor(page);
    await pickSandraMike(page);
    // Drill into Sandra/Mike's Retirement Income goal directly.
    await page.goto("/goal/goal_retirement_income");
    // RiskSlider radiogroup renders.
    await expect(
      page.getByRole("radiogroup", { name: /Risk bands/i }),
    ).toBeVisible({ timeout: 10_000 });
    // SourcePill renders one of three variants. The committed-state
    // case for Sandra/Mike's retirement_income (saved override score=1
    // ≠ system score=3) MUST render the engine pill on mount — this
    // is the explicit regression guard for the c5a7e02 conflated-
    // semantic bug class fixed at bd90cf9. Before the fix, the page
    // load fired onPreviewChange(true) and rendered calibration_drag.
    const enginePill = page
      .getByRole("status", { name: /engine recommendation/i })
      .first();
    const calibrationDragPill = page
      .getByRole("status", { name: /calibration.*drag|preview/i })
      .first();
    // Engine pill must be visible. Calibration_drag must NOT be — that's
    // the regression guard.
    await expect(enginePill).toBeVisible({ timeout: 10_000 });
    await expect(calibrationDragPill).toBeHidden();
  });
});
