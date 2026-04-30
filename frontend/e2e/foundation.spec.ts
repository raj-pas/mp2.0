/**
 * Phase R2 chrome smoke spec.
 *
 * Verifies the foundation surface for the v36 rewrite:
 *   - login → topbar visible with brand + client picker + report + methodology
 *   - role-based routing (advisor lands at /, analyst at /cma)
 *   - context panel renders for household route
 *   - methodology nav works
 *
 * Subsequent phases extend this spec with stage-specific assertions
 * (R3 — three-view stage, R5 — wizard, R7 — doc-drop, R9 — CMA, etc.).
 * The legacy `synthetic-review.spec.ts` and `portfolio-cma.spec.ts`
 * specs target deleted UI surfaces and are rebuilt at R7 / R9.
 */
import { expect, test } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";
const ANALYST_EMAIL = process.env.MP20_LOCAL_ANALYST_EMAIL ?? "analyst@example.com";
const ANALYST_PASSWORD = process.env.MP20_LOCAL_ANALYST_PASSWORD ?? "change-this-local-password";

test.describe("R2 chrome foundation", () => {
  test("advisor lands on household stage with topbar + ctx panel", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Email").fill(ADVISOR_EMAIL);
    await page.getByLabel("Password").fill(ADVISOR_PASSWORD);
    await page.getByRole("button", { name: /^Sign in$/i }).click();

    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("button", { name: /select client/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Report$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Methodology overlay/i })).toBeVisible();
    await expect(page.getByLabel(/Context panel/i).first()).toBeVisible();

    await expect(page.getByRole("heading", { name: /Household view/i })).toBeVisible();
  });

  test("methodology button navigates to /methodology", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Email").fill(ADVISOR_EMAIL);
    await page.getByLabel("Password").fill(ADVISOR_PASSWORD);
    await page.getByRole("button", { name: /^Sign in$/i }).click();

    await page.getByRole("button", { name: /Methodology overlay/i }).click();
    await expect(page).toHaveURL(/\/methodology$/);
    await expect(page.getByRole("heading", { name: /^Methodology$/ })).toBeVisible();
  });

  test("analyst is routed to CMA and cannot reach household", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Email").fill(ANALYST_EMAIL);
    await page.getByLabel("Password").fill(ANALYST_PASSWORD);
    await page.getByRole("button", { name: /^Sign in$/i }).click();

    await expect(page).toHaveURL(/\/cma$/);
    await expect(page.getByRole("heading", { name: /CMA Workbench/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /select client/i })).toHaveCount(0);
  });
});
