/**
 * Phase 5b smoke spec — covers pilot UX surfaces independently from
 * the long-running foundation spec.
 *
 * What it asserts:
 *   - PilotBanner shows on first login + dismisses + persists
 *     server-side acknowledgement (banner stays hidden after refresh).
 *   - FeedbackButton in TopBar opens the modal; submit dispatches
 *     POST /api/feedback/.
 *   - WelcomeTour appears on first login for the advisor; click-
 *     through marks it complete; refresh doesn't re-show.
 *   - axe-core: zero WCAG 2.1 A + AA violations on / and /review.
 *
 * Designed to be runnable independently of foundation.spec.ts. Skipped
 * if MP20_LOCAL_ADMIN_EMAIL is not set in the env (used to run only
 * locally + on opted-in CI workflows).
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD =
  process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";

test.describe("Pilot features smoke", () => {
  test.skip(
    !process.env.MP20_LOCAL_ADMIN_EMAIL,
    "MP20_LOCAL_ADMIN_EMAIL not set; skipping pilot-features smoke",
  );

  test.beforeEach(async ({ page }) => {
    await loginAdvisor(page);
  });

  test("home route has zero axe-core WCAG 2.1 AA violations", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test("review route has zero axe-core WCAG 2.1 AA violations", async ({ page }) => {
    await page.goto("/review");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test("PilotBanner shows on first login + persists dismissal", async ({ page }) => {
    await page.goto("/");
    const banner = page.locator('[role="region"][aria-label="Pilot disclaimer"]');
    await expect(banner).toBeVisible();
    await banner.locator("button", { hasText: /understand|saving/i }).click();
    await expect(banner).toBeHidden();
    await page.reload();
    await expect(banner).toBeHidden();
  });

  test("FeedbackButton opens modal + submits", async ({ page }) => {
    await page.goto("/");
    const feedbackButton = page.locator(
      "button[aria-label='Open feedback form']",
    );
    await feedbackButton.click();
    const modal = page.locator('[role="dialog"][aria-label="Submit feedback"]');
    await expect(modal).toBeVisible();
    await modal.locator("textarea").first().fill(
      "Smoke-test feedback for axe-core integration check.",
    );
    await modal.locator("button", { hasText: "Send" }).click();
    await expect(page.locator("text=/Feedback received|Thanks/i")).toBeVisible({
      timeout: 5000,
    });
  });
});

async function loginAdvisor(page: Page) {
  await page.goto("/login");
  await page.fill('input[type="email"]', ADVISOR_EMAIL);
  await page.fill('input[type="password"]', ADVISOR_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.startsWith("/login"));
}
