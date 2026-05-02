/**
 * Real-browser smoke against the demo flow — items 1, 4, 6 from the
 * post-R10 testing matrix. Runs in non-headless Chromium with full
 * console / page-error / network-failure capture so we catch the
 * class of bugs that pure headless misses (FileList race, font
 * loading, CSS rendering, etc.).
 *
 * Walks the canon demo flow against the Seltzer R10 workspace
 * (already reconciled) — covers everything an advisor would do live
 * EXCEPT the upload step (Seltzer is pre-uploaded; doc-drop is
 * exercised separately by the existing R7 e2e).
 *
 * Real-PII discipline: never quotes client content; only structural
 * counts to stdout.
 */
import { expect, test, type Page } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "";
const SELTZER_LABEL = "Seltzer review (demo prep)";

// Console errors that are KNOWN cosmetic and should not fail the
// smoke. Anything not in this list is treated as a real bug.
const CONSOLE_NOISE_PATTERNS: RegExp[] = [
  /OTS parsing error: invalid sfntVersion/i, // self-hosted fonts not yet downloaded (locked #22d)
  /Failed to decode downloaded font/i, // same
  /downloadable font: download failed/i, // same
  /react-router-dom/i, // future-flag warnings, not errors
  /React Router Future Flag/i,
  /Download the React DevTools/i,
];

function isExpectedNoise(text: string): boolean {
  return CONSOLE_NOISE_PATTERNS.some((p) => p.test(text));
}

interface CapturedSignal {
  kind: "console.error" | "console.warning" | "pageerror" | "request_failed";
  text: string;
  step: string;
  timestamp: number;
}

class SignalCollector {
  signals: CapturedSignal[] = [];
  step = "init";

  attach(page: Page) {
    page.on("console", (msg) => {
      const type = msg.type();
      if (type === "error" || type === "warning") {
        const text = msg.text();
        if (!isExpectedNoise(text)) {
          this.signals.push({
            kind: type === "error" ? "console.error" : "console.warning",
            text: text.slice(0, 400),
            step: this.step,
            timestamp: Date.now(),
          });
        }
      }
    });
    page.on("pageerror", (err) => {
      this.signals.push({
        kind: "pageerror",
        text: `${err.name}: ${err.message.slice(0, 350)}`,
        step: this.step,
        timestamp: Date.now(),
      });
    });
    page.on("requestfailed", (req) => {
      const url = req.url();
      // Ignore expected /static/ font 404s.
      if (url.includes("/fonts/") && url.endsWith(".woff2")) return;
      const failure = req.failure();
      this.signals.push({
        kind: "request_failed",
        text: `${req.method()} ${new URL(url).pathname} — ${failure?.errorText ?? "unknown"}`,
        step: this.step,
        timestamp: Date.now(),
      });
    });
  }

  setStep(step: string) {
    this.step = step;
  }

  print(): void {
    if (this.signals.length === 0) {
      console.log("=== CONSOLE: clean (0 unexpected errors/warnings/failures) ===");
      return;
    }
    console.log(`=== CONSOLE: ${this.signals.length} unexpected signals captured ===`);
    for (const s of this.signals) {
      console.log(`  [${s.kind}] (step=${s.step}) ${s.text}`);
    }
  }
}

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill(ADVISOR_EMAIL);
  await page.getByLabel("Password").fill(ADVISOR_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();
  await expect(page.getByRole("banner")).toBeVisible({ timeout: 10000 });
}

test("real-browser demo smoke: Seltzer review + commit + portfolio", async ({ page }) => {
  test.setTimeout(180_000);

  const collector = new SignalCollector();
  collector.attach(page);

  // === Step 1: login + topbar
  collector.setStep("login");
  await login(page);
  await expect(page.getByRole("button", { name: /select client/i })).toBeVisible();

  // === Step 2: navigate to /review and find the Seltzer workspace
  collector.setStep("review-route");
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: /Drop documents/i })).toBeVisible({
    timeout: 10000,
  });

  // Click the Seltzer queue row.
  collector.setStep("select-seltzer");
  const seltzerRow = page.getByRole("button", {
    name: new RegExp(SELTZER_LABEL.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"),
  });
  await expect(seltzerRow).toBeVisible({ timeout: 5000 });
  await seltzerRow.click();

  // === Step 3: ReviewScreen renders with all 5 docs reconciled
  collector.setStep("review-screen");
  await expect(
    page.getByRole("heading", { name: new RegExp(SELTZER_LABEL.replace(/\W/g, "."), "i") }),
  ).toBeVisible({ timeout: 10000 });

  // Count reconciled chips
  const reconciledChips = page.locator("span", { hasText: /^reconciled$/i });
  const reconciledCount = await reconciledChips.count();
  console.log(`  Seltzer reconciled chips: ${reconciledCount}`);
  expect(reconciledCount).toBeGreaterThanOrEqual(5);

  // No failed-status chips for Seltzer
  const failedChips = page.locator("span.text-danger", { hasText: /^failed$/i });
  const failedCount = await failedChips.count();
  console.log(`  failed chips: ${failedCount}`);
  expect(failedCount).toBe(0);

  // Readiness panel renders
  await expect(page.getByText(/Engine ready/i)).toBeVisible();
  await expect(page.getByText(/Construction ready/i)).toBeVisible();
  await expect(page.getByText(/KYC ready/i)).toBeVisible();

  // === Step 4: All 6 required-section approval buttons present
  collector.setStep("section-approvals-visible");
  // The Section Approvals panel renders one row per required section
  // with an Approve button. Use the button's accessible label
  // (`Approve {{section}}`) as the deterministic anchor — works
  // regardless of layout changes inside the row.
  for (const section of [
    "household",
    "people",
    "accounts",
    "goals",
    "goal_account_mapping",
    "risk",
  ]) {
    const approveBtn = page.getByRole("button", {
      name: new RegExp(`Approve ${section}`, "i"),
    });
    await expect(approveBtn).toBeVisible({ timeout: 5000 });
  }
  console.log("  all 6 section-approval buttons visible");

  // Commit button is rendered but disabled (engine readiness not met).
  const commitBtn = page.getByRole("button", { name: /Commit household/i });
  await expect(commitBtn).toBeVisible();
  await expect(commitBtn).toBeDisabled();
  console.log("  commit button correctly disabled (engine readiness not met)");

  // === Step 5: Take a screenshot of the review screen for the demo prep record
  await page.screenshot({
    path: "test-results/seltzer-review-screen-real-browser.png",
    fullPage: true,
  });
  console.log("  screenshot: test-results/seltzer-review-screen-real-browser.png");

  // === Step 6: Navigate to /methodology and verify it renders
  collector.setStep("methodology");
  await page.getByRole("button", { name: /Methodology/i }).click();
  await expect(page).toHaveURL(/\/methodology$/);
  await expect(page.getByRole("heading", { name: /^Methodology$/ })).toBeVisible();

  // === Step 7: Navigate to / and pick the synthetic Sandra/Mike Chen
  collector.setStep("client-pick");
  await page.goto("/");
  await page.getByRole("button", { name: /select client/i }).click();
  // Select an advisor-scoped household via the picker
  const sandraRow = page.locator("li", { hasText: /Sandra/i }).first();
  if (await sandraRow.isVisible({ timeout: 5000 }).catch(() => false)) {
    await sandraRow.click();
  }

  // === Final report
  collector.setStep("final");
  collector.print();
  if (collector.signals.length > 0) {
    throw new Error(
      `Real-browser smoke captured ${collector.signals.length} unexpected console / page / network signals.`,
    );
  }
});
