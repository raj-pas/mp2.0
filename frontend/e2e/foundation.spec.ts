/**
 * R2 + R3 + R4 + R5 + R6 + R7 foundation smoke spec.
 *
 * Verifies the v36 rewrite shell up through doc-drop / review-screen:
 *   - login → topbar visible (brand + picker + report + methodology)
 *   - role-based routing (advisor lands at /, analyst at /cma)
 *   - context panel renders alongside the household stage
 *   - methodology nav works
 *   - advisor: pick a client → AUM strip + treemap render
 *   - advisor: navigate / → /account/:id → /goal/:id surfaces render
 *   - advisor: goal page shows RiskSlider + Allocation + Optimizer +
 *     Moves + ProjectionsFan; override save round-trips through the
 *     audit log
 *   - advisor: 5-step wizard creates a household end-to-end and
 *     redirects to the new household stage
 *   - advisor: re-goal modal applies a balance-preserving leg shift
 *     and the History tab shows the new before/after snapshots
 *   - advisor: doc-drop creates a synthetic workspace, uploads a file,
 *     and the review queue shows it in flight
 *
 * Subsequent phases extend this spec (R8 methodology, R9 CMA, R10 polish).
 */
import { expect, test, type Page } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";
const ANALYST_EMAIL = process.env.MP20_LOCAL_ANALYST_EMAIL ?? "analyst@example.com";
const ANALYST_PASSWORD = process.env.MP20_LOCAL_ANALYST_PASSWORD ?? "change-this-local-password";

async function loginAdvisor(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill(ADVISOR_EMAIL);
  await page.getByLabel("Password").fill(ADVISOR_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();
}

async function loginAnalyst(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill(ANALYST_EMAIL);
  await page.getByLabel("Password").fill(ANALYST_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();
}

test.describe("R2 chrome", () => {
  test("advisor sees topbar and context panel after login", async ({ page }) => {
    await loginAdvisor(page);

    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("button", { name: /select client/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Report$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Methodology/i })).toBeVisible();
    await expect(page.getByLabel(/Context panel/i).first()).toBeVisible();
  });

  test("methodology button navigates to /methodology", async ({ page }) => {
    await loginAdvisor(page);

    await page.getByRole("button", { name: /Methodology/i }).click();
    await expect(page).toHaveURL(/\/methodology$/);
    await expect(page.getByRole("heading", { level: 1, name: /^Methodology$/ })).toBeVisible();
  });

  test("R8 methodology overlay renders all 10 sections + canon-aligned descriptors", async ({
    page,
  }) => {
    await loginAdvisor(page);
    // Wait for login mutation to land before navigating; otherwise
    // /methodology bounces to LoginRoute via SessionGate.
    await expect(page.getByRole("banner")).toBeVisible({ timeout: 10000 });
    await page.goto("/methodology");
    await expect(page.getByRole("heading", { level: 1, name: /^Methodology$/ })).toBeVisible({
      timeout: 10000,
    });

    // All 10 section headings render (uses level 2 inside SectionShell).
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
      await expect(page.getByRole("heading", { level: 2, name: sectionTitle })).toBeVisible();
    }

    // Locked-decision-#5 canon descriptors must appear in the horizon-cap
    // table. The retired mockup labels (Conservative, Cautious as separate
    // bucket from Cautious-balanced, Growth) must NOT appear as the
    // canon-1 descriptor.
    for (const descriptor of [
      "Cautious",
      "Conservative-balanced",
      "Balanced",
      "Balanced-growth",
      "Growth-oriented",
    ]) {
      await expect(page.getByText(descriptor, { exact: true }).first()).toBeVisible();
    }

    // Locked-decision-#6: Goal_50 must appear ONLY in a footnote, not as
    // the headline of section 3. The section title is "Goal-level risk
    // score", not "Goal_50".
    await expect(page.getByRole("heading", { name: /Goal_50/i })).toHaveCount(0);

    // TOC link → scroll behavior. Click the §06 entry, expect Sleeve mix
    // section to be the visible one (scroll-into-view).
    await page.getByRole("button", { name: /Sleeve mix/i }).click();
    await expect(page.getByRole("heading", { level: 2, name: /Sleeve mix/i })).toBeInViewport();
  });

  test("analyst routes to CMA and cannot reach household controls", async ({ page }) => {
    await loginAnalyst(page);

    await expect(page).toHaveURL(/\/cma$/);
    await expect(page.getByRole("heading", { name: /CMA Workbench/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /select client/i })).toHaveCount(0);
  });
});

test.describe("R3 three-view stage", () => {
  test("advisor picks a client and sees AUM strip + treemap", async ({ page }) => {
    await loginAdvisor(page);

    // Open client picker and choose first available client.
    await page.getByRole("button", { name: /select client/i }).click();
    const firstClientOption = page.getByRole("option").first();
    await expect(firstClientOption).toBeVisible();
    const clientName = (await firstClientOption.textContent())?.trim() ?? "";
    await firstClientOption.click();

    // Topbar reflects the selected client.
    await expect(
      page.getByRole("button", { name: /select client/i }),
    ).toContainText(clientName.split("$")[0]?.trim() ?? clientName);

    // Household stage: AUM strip aria-label + treemap SVG (role=img).
    await expect(page.getByLabel(/Total AUM/i)).toBeVisible();
    await expect(page.getByRole("img", { name: /treemap, grouped/i })).toBeVisible();
  });

  test("advisor navigates household → account → goal", async ({ page }) => {
    await loginAdvisor(page);

    await page.getByRole("button", { name: /select client/i }).click();
    await page.getByRole("option").first().click();

    // Click first account in the treemap (rendered as accessible button).
    const accountTile = page.getByRole("button", { name: /\$/ }).first();
    await expect(accountTile).toBeVisible();
    await accountTile.click();
    await expect(page).toHaveURL(/\/account\/.+/);
    await expect(page.getByLabel(/Account value/i)).toBeVisible();

    // Click first goal-in-account row to drill into goal.
    const firstGoalLink = page.getByRole("link").filter({ hasText: /\$/ }).first();
    if ((await firstGoalLink.count()) > 0) {
      await firstGoalLink.click();
      await expect(page).toHaveURL(/\/goal\/.+/);
      // Two RiskBandTrack meters render on goal page (KPI tile +
      // ctx-panel overview). Either one being visible is sufficient.
      await expect(page.getByRole("meter").first()).toBeVisible();
    }
  });
});

test.describe("R4 goal allocation + override", () => {
  test("advisor sees RiskSlider + allocation + optimizer + moves on goal", async ({
    page,
  }) => {
    await loginAdvisor(page);

    // Pick the synthetic Sandra/Mike Chen client (has known goals).
    await page.getByRole("button", { name: /select client/i }).click();
    const sandraOption = page.getByRole("option", { name: /Sandra/i });
    await expect(sandraOption).toBeVisible();
    await sandraOption.click();

    // Navigate directly to the retirement goal — synthetic persona has it.
    await page.goto("/goal/goal_retirement_income");

    // RiskSlider radiogroup
    await expect(page.getByRole("radiogroup", { name: /Risk bands/i })).toBeVisible();

    // GoalAllocationSection table headers
    await expect(page.getByRole("columnheader", { name: /Current/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Ideal/i })).toBeVisible();

    // Optimizer output widget (one of the headings); use a regex for
    // the "Improvement at P5" / "P15" / "P25" pattern from the API.
    await expect(page.getByText(/Improvement at P/i)).toBeVisible();

    // Moves section heading
    await expect(page.getByText(/Express as moves/i)).toBeVisible();

    // ProjectionsFan should mount within the latency budget; the SVG
    // canvas is wrapped in a role="img" with the projection aria-label.
    await expect(
      page.getByRole("img", { name: /projection fan/i }),
    ).toBeVisible({ timeout: 10000 });
  });

  test("advisor saves a goal-risk override and sees it in history", async ({ page }) => {
    await loginAdvisor(page);
    await page.getByRole("button", { name: /select client/i }).click();
    await page.getByRole("option", { name: /Sandra/i }).click();
    await page.goto("/goal/goal_retirement_income");

    // Pick a band different from system score (system on Sandra's
    // retirement goal is "Balanced" = 3; choose "Cautious" = band 1).
    const cautiousBand = page.getByRole("radio", { name: /Cautious \(1 \/ 5\)/ });
    await expect(cautiousBand).toBeVisible();
    await cautiousBand.click();

    // Override banner appears.
    await expect(page.getByText(/Override active/i)).toBeVisible();

    // Rationale textarea + save button.
    const stamp = Date.now();
    const rationale = `R4 e2e override smoke ${stamp}`;
    await page.getByLabel(/Rationale/i).fill(rationale);
    await page.getByRole("button", { name: /Save override/i }).click();

    // Override history shows in ctx-panel projections tab.
    await page.getByRole("tab", { name: /Projections/i }).click();
    await expect(page.getByText(rationale)).toBeVisible({ timeout: 10000 });
  });
});

test.describe("R5 wizard onboarding", () => {
  test("advisor walks the 5-step wizard and commits a household", async ({ page }) => {
    test.setTimeout(60_000);
    await loginAdvisor(page);

    // Open client picker → "Add new household"
    await page.getByRole("button", { name: /select client/i }).click();
    await page.getByRole("button", { name: /Add new household/i }).click();
    await expect(page).toHaveURL(/\/wizard\/new$/);

    // Step 1 — identity
    const stamp = Date.now();
    const householdName = `R5 Smoke Wizard ${stamp}`;
    await page.getByPlaceholder(/Yeager Household/i).fill(householdName);
    // Member 1 inputs
    const memberInputs = page.locator('input[name^="members."]');
    await memberInputs.nth(0).fill("Smoke Smith");
    await memberInputs.nth(1).fill("1975-04-15");
    await page.getByRole("button", { name: /^Next$/ }).click();

    // Step 2 — risk profile (defaults Q1=5, Q2=B, Q4=B → Balanced/3)
    await expect(page.getByText(/Live recompute/i)).toBeVisible();
    // Wait for the live preview's canon-score readout (debounced 250ms +
    // network roundtrip). The Stat dt label is exactly "Tolerance (T)".
    await expect(
      page.getByRole("definition").filter({ hasText: /\/100/ }).first(),
    ).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: /^Next$/ }).click();

    // Step 3 — accounts + goals
    // Default account is RRSP at index 0; fill its current_value.
    const accountValueInput = page
      .locator('input[name^="accounts."]')
      .filter({ hasText: "" })
      .nth(0);
    // The first numeric input under accounts is `accounts.0.current_value`
    await page.locator('input[name="accounts.0.current_value"]').fill("180000");
    // Default goal — fill name, target date, target amount, leg amount.
    await page.locator('input[name="goals.0.name"]').fill("Retirement");
    await page.locator('input[name="goals.0.target_date"]').fill("2045-12-31");
    await page.locator('input[name="goals.0.target_amount"]').fill("1500000");
    await page.locator('input[name="goals.0.legs.0.allocated_amount"]').fill("180000");
    void accountValueInput;
    await page.getByRole("button", { name: /^Next$/ }).click();

    // Step 4 — external holdings (skippable)
    await expect(page.getByRole("heading", { name: /External holdings/i })).toBeVisible();
    await page.getByRole("button", { name: /^Next$/ }).click();

    // Step 5 — review + commit
    await expect(page.getByRole("heading", { name: /Review and commit/i })).toBeVisible();
    await expect(page.getByText(householdName)).toBeVisible();
    await page.getByRole("button", { name: /^Commit household$/ }).click();

    // After commit we land on `/` and the topbar reflects the new
    // household name.
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 });
    await expect(page.getByRole("button", { name: /select client/i })).toContainText(
      householdName.slice(0, 16),
      { timeout: 10000 },
    );
  });
});

test.describe("R6 realignment + history", () => {
  test("advisor re-goals a balance-preserving leg shift and sees it in history", async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await loginAdvisor(page);

    // Pick Sandra/Mike Chen — has multiple legs ready to re-goal.
    await page.getByRole("button", { name: /select client/i }).click();
    await page.getByRole("option", { name: /Sandra/i }).click();

    // Re-goal CTA opens the modal.
    await page.getByRole("button", { name: /Re-goal across accounts/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText(/Re-goaling re-labels dollars between goals/i)).toBeVisible();

    // Apply without changing values (the seeded household is balanced)
    // — this still creates before/after snapshots and records audit.
    const applyButton = page.getByRole("button", { name: /^Apply re-goal$/ });
    await expect(applyButton).toBeEnabled();
    await applyButton.click();

    // CompareScreen opens with Confirm + Revert affordances.
    await expect(page.getByRole("heading", { name: /Confirm or revert/i })).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByRole("button", { name: /Keep after-state/i })).toBeVisible();

    // Confirm closes the screen.
    await page.getByRole("button", { name: /Keep after-state/i }).click();

    // Open the right ctx-panel and switch to the History tab.
    await page.getByRole("tab", { name: /^History$/ }).click();

    // The new before/after snapshots should appear (label "After realignment"
    // is the newest row).
    await expect(page.getByText(/After realignment/).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Before realignment/).first()).toBeVisible();
  });
});

test.describe("R7 doc-drop + review queue", () => {
  test("advisor uploads a synthetic doc and sees it in the review queue", async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await loginAdvisor(page);
    // Wait for the chrome to render — login mutation must land before
    // we navigate, otherwise SessionGate renders LoginRoute again.
    await expect(page.getByRole("banner")).toBeVisible();

    await page.goto("/review");

    // Doc-drop overlay is visible.
    await expect(page.getByRole("heading", { name: /Drop documents/i })).toBeVisible({
      timeout: 10_000,
    });

    // Fill workspace label + ensure synthetic origin is selected.
    const stamp = Date.now();
    const label = `R7 e2e doc-drop ${stamp}`;
    await page.getByPlaceholder(/Yeager Household/i).fill(label);

    // Pick a synthetic file from the test runner (write a tiny temp file
    // and use the hidden file input that DocDropOverlay surfaces).
    const buffer = Buffer.from(
      [
        "Synthetic onboarding doc for R7 e2e.",
        "Household: Smoke E2E Household.",
        "Person: Smoke E2E age 50.",
        "Account: TFSA value 100000.",
      ].join("\n"),
    );
    await page.setInputFiles('input[type="file"]', {
      name: "smoke-e2e.txt",
      mimeType: "text/plain",
      buffer,
    });

    // Regression guard: the live `FileList` reference returned by
    // `event.target.files` becomes empty when the input is cleared
    // (`event.target.value = ""`). The handler MUST snapshot
    // `Array.from(...)` synchronously before clearing — otherwise React's
    // deferred `setFiles` callback observes an empty list and the file
    // never lands in state. The "1 FILE READY TO UPLOAD" counter is the
    // user-visible signal that the snapshot worked.
    await expect(page.getByText(/1 FILE READY TO UPLOAD/i)).toBeVisible({
      timeout: 3000,
    });

    // Start the review.
    await page.getByRole("button", { name: /^Start review$/ }).click();

    // The new workspace should appear in the in-flight queue and be
    // selected automatically; the ReviewScreen renders the workspace
    // label as its heading.
    await expect(
      page.getByRole("heading", { name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) }),
    ).toBeVisible({ timeout: 15000 });

    // Readiness panel renders with engine_ready/construction_ready
    // both false (no extracted data yet).
    await expect(page.getByText(/Engine ready/i)).toBeVisible();
    await expect(page.getByText(/Construction ready/i)).toBeVisible();
  });
});

test.describe("R9 CMA Workbench", () => {
  test("analyst sees all 5 tabs and the snapshots list renders", async ({ page }) => {
    await loginAnalyst(page);

    // Lands on /cma per role-based routing.
    await expect(page).toHaveURL(/\/cma$/);
    await expect(page.getByRole("heading", { level: 1, name: /CMA Workbench/i })).toBeVisible();

    // All 5 tabs render
    for (const tab of ["Snapshots", "Assumptions", "Correlations", "Frontier", "Audit"]) {
      await expect(page.getByRole("tab", { name: tab })).toBeVisible();
    }

    // Snapshots tab is the default — table headers visible
    await expect(page.getByText(/^Version$/i).first()).toBeVisible();
    await expect(page.getByText(/^Status$/i).first()).toBeVisible();

    // At least one snapshot row exists (Default CMA seeded by reset script).
    await expect(page.getByText(/Default CMA/i).first()).toBeVisible({ timeout: 5000 });

    // Wait for the active snapshot to load (the CmaHeader pill renders
    // "Active: ..." once activeQuery resolves; until then Frontier tab
    // would short-circuit at "Select a snapshot first").
    await expect(page.getByText(/Active:/i)).toBeVisible({ timeout: 10000 });

    // Assumptions tab loads the active snapshot
    await page.getByRole("tab", { name: "Assumptions" }).click();
    // Fund column header
    await expect(page.getByText(/Expected return/i).first()).toBeVisible();

    // Frontier tab renders without crash. The canvas only mounts after
    // (a) selectedId is non-null AND (b) frontierQuery resolves AND
    // (c) the dynamic chart.js import resolves — wait for the summary
    // line below the canvas which only appears after data loads.
    await page.getByRole("tab", { name: "Frontier" }).click();
    await expect(page.getByText(/efficient frontier points/i)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator("canvas").first()).toBeVisible({ timeout: 5000 });

    // Audit tab renders the recent CMA actions list (or the empty state)
    await page.getByRole("tab", { name: "Audit" }).click();
    // The page shouldn't crash — heading still visible
    await expect(page.getByRole("heading", { level: 1, name: /CMA Workbench/i })).toBeVisible();
  });

  test("advisor cannot access /cma surface (silent server-side 403)", async ({ page }) => {
    await loginAdvisor(page);
    await expect(page.getByRole("banner")).toBeVisible();

    // Navigate to /cma directly — UI should surface the forbidden state
    // instead of silently rendering an empty Workbench.
    await page.goto("/cma");
    // The forbidden message names "financial-analyst role" so analysts
    // know who has access (canon §11.8 + locked decision #5).
    await expect(page.getByText(/financial.analyst/i)).toBeVisible({ timeout: 5000 });
  });
});
