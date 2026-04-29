import { expect, test } from "@playwright/test";

test("advisor can generate a portfolio run and view run history", async ({ page }) => {
  const email = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
  const password = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";

  await page.goto("/");
  await page.getByPlaceholder("Email").fill(email);
  await page.getByPlaceholder("Password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await expect(page.getByText(email)).toBeVisible();

  await expect(page.getByRole("heading", { name: /Sandra & Mike Chen/i })).toBeVisible();
  await page.getByRole("button", { name: /Generate Portfolio/i }).click();

  await expect(
    page.getByRole("heading", { name: /Goal-Account Recommendations/i }),
  ).toBeVisible();
  await expect(page.getByText(/Why this recommendation/i)).toBeVisible();
  await expect(page.getByText(/Run History/i)).toBeVisible();
  await expect(page.getByText(/default_cma_link_frontier_v1/i).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "CMA" })).toHaveCount(0);
});

test("financial analyst can use the CMA Workbench", async ({ page }) => {
  const email = process.env.MP20_LOCAL_ANALYST_EMAIL ?? "analyst@example.com";
  const password = process.env.MP20_LOCAL_ANALYST_PASSWORD ?? "change-this-local-password";

  await page.goto("/");
  await page.getByPlaceholder("Email").fill(email);
  await page.getByPlaceholder("Password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await expect(page.getByText(email)).toBeVisible();

  await page.getByRole("button", { name: "CMA" }).click();
  await expect(page.getByRole("heading", { name: /CMA Workbench/i })).toBeVisible();
  const apiBase = process.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const deniedClients = await page.request.get(`${apiBase}/api/clients/`);
  expect(deniedClients.status()).toBe(403);
  await expect(page.getByText(/Active Snapshot/i)).toBeVisible();
  await expect(page.getByText(/Default CMA/i).first()).toBeVisible();

  await page.getByRole("button", { name: /New Draft|Open Draft/i }).first().click();
  await expect(page.getByRole("button", { name: /Assumptions/i })).toHaveClass(/border-spruce/);
  await page.locator('input[type="number"]').nth(1).fill("-0.1");
  await expect(page.getByText(/volatility must be between/i)).toBeVisible();
  await page.locator('input[type="number"]').nth(1).fill("0.13312");
  await page.locator('input[type="number"]').first().fill("0.0712");
  const smallCapEligible = page.getByLabel(/SH Small Cap Equity eligible/i);
  await smallCapEligible.uncheck();
  await expect(smallCapEligible).not.toBeChecked();
  await smallCapEligible.check();
  await expect(smallCapEligible).toBeChecked();
  await page.getByRole("button", { name: /Save Draft/i }).click();
  await expect(page.getByRole("button", { name: /Save Draft/i })).toBeEnabled();

  await page.getByRole("button", { name: /Correlations/i }).click();
  await page.getByLabel(/SH Equity to SH Income correlation/i).first().fill("0.6");
  await page.getByRole("button", { name: /Save Draft/i }).click();
  await expect(page.getByRole("button", { name: /Save Draft/i })).toBeEnabled();

  await page.getByRole("button", { name: /Frontier/i }).click();
  await expect(page.getByText(/efficient points/i)).toBeVisible();
  await expect(page.getByLabel(/Efficient frontier chart/i)).toBeVisible();
  await expect(page.getByText(/SH Small Cap Equity/i)).toBeVisible();

  await page.getByRole("button", { name: /Assumptions/i }).click();
  await page.locator('input[type="number"]').first().fill("0.0731");
  await page.getByRole("button", { name: /Save Draft/i }).click();
  await expect(page.getByRole("button", { name: /Save Draft/i })).toBeEnabled();
  await page.getByRole("button", { name: /Correlations/i }).click();
  await page.getByLabel(/SH Equity to SH Income correlation/i).first().fill("0.613");
  await page.getByRole("button", { name: /Save Draft/i }).click();
  await expect(page.getByRole("button", { name: /Save Draft/i })).toBeEnabled();

  await page.getByRole("button", { name: /Snapshots/i }).click();
  await page.getByLabel(/Publish note/i).fill("E2E analyst publish note.");
  await page.getByRole("button", { name: /^Publish$/i }).click();
  await expect(page.getByText(/E2E analyst publish note/i).first()).toBeVisible();

  await page.getByRole("button", { name: /Audit/i }).click();
  await expect(page.getByText(/E2E analyst publish note/i).first()).toBeVisible();
  const legacyRuntimeLabels = new RegExp(
    ["Fra" + "ser", "mp20_" + "scenario", "draft" + " draft"].join("|"),
    "i",
  );
  await expect(page.locator("body")).not.toContainText(legacyRuntimeLabels);
});
