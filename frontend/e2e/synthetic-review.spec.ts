import { expect, type Locator, type Page, test } from "@playwright/test";
import { writeFile } from "node:fs/promises";

test("synthetic review reaches approved commit path", async ({ page }, testInfo) => {
  const email = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
  const password = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";
  const workspaceLabel = `Synthetic E2E ${Date.now()}`;
  const uploadPath = testInfo.outputPath("mp20-synthetic-statement.txt");
  await writeFile(
    uploadPath,
    [
      "Synthetic statement for MP2.0 browser E2E.",
      "Household: Synthetic Browser Household",
      "Person: Browser Client age 62.",
      "Account: RRSP value 250000.",
      "Goal: Retirement horizon 5 years.",
    ].join("\n"),
  );

  await page.goto("/");
  await page.getByPlaceholder("Email").fill(email);
  await page.getByPlaceholder("Password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await expect(page.getByText(email)).toBeVisible();

  await page.getByRole("button", { name: "Review" }).click();
  await page.getByPlaceholder("Household or bundle label").fill(workspaceLabel);
  await page.locator("select").first().selectOption("synthetic");
  await page.getByRole("button", { name: /Create Workspace/i }).click();
  await expect(page.getByRole("button", { name: new RegExp(workspaceLabel) })).toBeVisible();

  await page.locator('input[type="file"]').setInputFiles(uploadPath);
  await page.getByRole("button", { name: /Upload Files/i }).click();
  await expect(page.getByText(/Uploaded 1; duplicates 0/i)).toBeVisible();
  await expect(page.getByText(/mp20-synthetic-statement.txt/i)).toBeVisible();
  await expect(page.getByText(/reconciled/i).first()).toBeVisible();

  await page.getByRole("button", { name: /^People$/i }).click();
  await page.getByPlaceholder("Add member").fill("Browser Client");
  await clickAndWaitForStatePatch(page, page.getByRole("button", { name: /^Member$/i }));

  await page.getByRole("button", { name: /^Accounts$/i }).click();
  await page.getByPlaceholder("Account value").fill("250000");
  await clickAndWaitForStatePatch(page, page.getByRole("button", { name: /^Account$/i }));

  await page.getByRole("button", { name: /^Goals$/i }).click();
  await clickAndWaitForStatePatch(page, page.getByRole("button", { name: /^Goal$/i }));

  await page.getByRole("button", { name: /^Goal Account Mapping$/i }).click();
  await clickAndWaitForStatePatch(
    page,
    page.getByRole("button", { name: /Confirm First Goal\/Account Mapping/i }),
  );

  for (const section of [
    /Save household approval/i,
    /Save people approval/i,
    /Save accounts approval/i,
    /Save goals approval/i,
    /Save goal account mapping approval/i,
    /Save risk approval/i,
  ]) {
    await clickAndWaitForApproval(page, page.getByRole("button", { name: section }));
  }

  await expect(page.getByText(/Required sections must be approved/i)).toBeHidden();
  await page.getByRole("button", { name: /Create Household/i }).click();
  await expect(page.getByText(workspaceLabel)).toBeVisible();
  await page.getByRole("button", { name: /Generate Portfolio/i }).click();
  await expect(
    page.getByRole("heading", { name: /Goal-Account Recommendations/i }),
  ).toBeVisible();
  await expect(page.getByText(/Run History/i)).toBeVisible();
});

async function clickAndWaitForStatePatch(page: Page, locator: Locator) {
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes("/state/") &&
        response.request().method() === "PATCH" &&
        response.status() === 200,
    ),
    locator.click(),
  ]);
}

async function clickAndWaitForApproval(page: Page, locator: Locator) {
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes("/approve-section/") &&
        response.request().method() === "POST" &&
        response.status() === 200,
    ),
    locator.click(),
  ]);
}
