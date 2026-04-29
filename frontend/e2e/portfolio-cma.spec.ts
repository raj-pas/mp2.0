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
  await expect(page.getByText(/fraser_link_frontier_v1/i).first()).toBeVisible();
});

test("financial analyst can edit CMA draft and view frontier", async ({ page }) => {
  const email = process.env.MP20_LOCAL_ANALYST_EMAIL ?? "analyst@example.com";
  const password = process.env.MP20_LOCAL_ANALYST_PASSWORD ?? "change-this-local-password";

  await page.goto("/");
  await page.getByPlaceholder("Email").fill(email);
  await page.getByPlaceholder("Password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await expect(page.getByText(email)).toBeVisible();

  await page.getByRole("button", { name: "CMA" }).click();
  await expect(page.getByRole("heading", { name: /CMA & Frontier/i })).toBeVisible();
  await expect(page.getByText(/Active Snapshot/i)).toBeVisible();
  await expect(page.getByText(/efficient points/i)).toBeVisible();
  await expect(page.locator('[title^="Return "]').first()).toBeVisible();

  await page.getByRole("button", { name: /New Draft/i }).click();
  await expect(page.getByRole("heading", { name: /Fraser CMA draft/i })).toBeVisible();
  await page.locator('input[type="number"]').first().fill("0.0712");
  await page.getByRole("button", { name: /Save Draft/i }).click();
  await expect(page.getByRole("button", { name: /Save Draft/i })).toBeEnabled();
  await page.getByRole("button", { name: /^Publish$/i }).click();
  await expect(page.getByRole("heading", { name: /Fraser CMA draft/i })).toBeHidden();
  await expect(page.getByText(/Active Snapshot/i)).toBeVisible();
});
