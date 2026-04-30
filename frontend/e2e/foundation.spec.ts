/**
 * R2 + R3 foundation smoke spec.
 *
 * Verifies the v36 rewrite shell up through the three-view stage:
 *   - login → topbar visible (brand + picker + report + methodology)
 *   - role-based routing (advisor lands at /, analyst at /cma)
 *   - context panel renders alongside the household stage
 *   - methodology nav works
 *   - advisor: pick a client → AUM strip + treemap render
 *   - advisor: navigate / → /account/:id → /goal/:id surfaces render
 *
 * Subsequent phases extend this spec (R5 wizard, R7 doc-drop, R9 CMA).
 * The legacy `synthetic-review.spec.ts` / `portfolio-cma.spec.ts` specs
 * targeted the old shell deleted in R0 and are rebuilt at R7 / R9.
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
    await expect(page.getByRole("button", { name: /Methodology overlay/i })).toBeVisible();
    await expect(page.getByLabel(/Context panel/i).first()).toBeVisible();
  });

  test("methodology button navigates to /methodology", async ({ page }) => {
    await loginAdvisor(page);

    await page.getByRole("button", { name: /Methodology overlay/i }).click();
    await expect(page).toHaveURL(/\/methodology$/);
    await expect(page.getByRole("heading", { name: /^Methodology$/ })).toBeVisible();
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
      await expect(page.getByLabel(/Target/i).first()).toBeVisible();
      await expect(page.getByRole("meter")).toBeVisible();
    }
  });
});
