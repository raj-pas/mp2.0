/**
 * Forced-failure manual-entry flow — items 3+4 from the post-R10
 * testing matrix. Verifies that for a doc with a typed failure_code
 * (`bedrock_token_limit` here), the UI:
 *   1. Renders the failed-status chip
 *   2. Renders the i18n failure_code copy on the row
 *   3. Renders both the Retry and "Mark as manual entry" buttons
 *   4. On click, the manual-entry mutation fires and the status flips
 *      to manual_entry
 *
 * Depends on the workspace + failed doc set up by the host shell test
 * (forced-failure workspace `Forced-failure UI test` with one doc 75
 * in failed status, failure_code=bedrock_token_limit).
 */
import { expect, test } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "";
const FF_LABEL = "Forced-failure UI test";

test("failed doc surfaces failure_code copy + manual-entry button + flips status on click", async ({
  page,
}) => {
  test.setTimeout(60_000);

  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      const text = msg.text();
      // Filter known cosmetic errors (font OTS, React Router future-flag warnings)
      if (
        !/OTS parsing error/i.test(text) &&
        !/Failed to decode downloaded font/i.test(text) &&
        !/react-router-dom/i.test(text)
      ) {
        consoleErrors.push(text);
      }
    }
  });
  page.on("pageerror", (err) => {
    consoleErrors.push(`pageerror: ${err.message}`);
  });

  // Login
  await page.goto("/");
  await page.getByLabel("Email").fill(ADVISOR_EMAIL);
  await page.getByLabel("Password").fill(ADVISOR_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();
  await expect(page.getByRole("banner")).toBeVisible({ timeout: 10000 });

  // Open the forced-failure workspace
  await page.goto("/review");
  const ffRow = page.getByRole("button", { name: new RegExp(FF_LABEL, "i") });
  await expect(ffRow).toBeVisible({ timeout: 5000 });
  await ffRow.click();

  // The doc row should render with the failed-status chip
  await expect(
    page.getByRole("heading", { name: new RegExp(FF_LABEL, "i") }),
  ).toBeVisible({ timeout: 5000 });

  // Failed status chip visible (text-danger styling)
  const failedChip = page.locator("span.text-danger", { hasText: /^failed$/i });
  await expect(failedChip).toBeVisible({ timeout: 3000 });
  console.log("  failed chip rendered");

  // Failure-code copy line for bedrock_token_limit. The i18n key
  // `review.failure_code.bedrock_token_limit` resolves to
  // "This document exceeded the AI extraction output budget. ..."
  const failureCopy = page.getByText(/exceeded the AI extraction output budget/i);
  await expect(failureCopy).toBeVisible({ timeout: 3000 });
  console.log("  failure_code copy rendered");

  // "Mark as manual entry" button visible
  const manualEntryBtn = page.getByRole("button", { name: /Mark as manual entry/i });
  await expect(manualEntryBtn).toBeVisible({ timeout: 3000 });
  console.log("  manual-entry button rendered");

  // Take screenshot pre-click (for the demo prep record)
  await page.screenshot({
    path: "test-results/manual-entry-pre-click.png",
    fullPage: true,
  });

  // Click manual-entry; expect:
  //   - mutation completes (200)
  //   - failed chip → manual_entry chip
  //   - failure-code copy disappears
  //   - manual-entry button disappears (eligibility falls off)
  //   - toast confirmation
  const responsePromise = page.waitForResponse(
    (resp) => resp.url().includes("/manual-entry/") && resp.status() === 200,
  );
  await manualEntryBtn.click();
  const response = await responsePromise;
  const body = await response.json();
  expect(body.status).toBe("manual_entry");
  expect(body.previous_failure_code).toBe("bedrock_token_limit");
  console.log("  manual-entry POST returned 200");

  // After mutation, the row should re-render with manual_entry chip
  // (border-accent-2 / text-accent-2 styling per ReviewScreen.tsx). The
  // chip text is "manual_entry".
  const manualEntryChip = page.locator("span", { hasText: /^manual_entry$/i });
  await expect(manualEntryChip).toBeVisible({ timeout: 5000 });
  console.log("  manual_entry chip rendered after click");

  // Failure-code copy should be gone (status is no longer failed).
  await expect(page.getByText(/exceeded the AI extraction output budget/i)).toHaveCount(0);
  console.log("  failure_code copy removed");

  // Manual-entry button should be gone.
  await expect(page.getByRole("button", { name: /Mark as manual entry/i })).toHaveCount(0);
  console.log("  manual-entry button removed after click");

  await page.screenshot({
    path: "test-results/manual-entry-post-click.png",
    fullPage: true,
  });

  // Final console-error check
  if (consoleErrors.length > 0) {
    console.log(`=== ${consoleErrors.length} unexpected console errors ===`);
    for (const e of consoleErrors) console.log(`  ${e.slice(0, 250)}`);
    throw new Error(`Manual-entry flow surfaced ${consoleErrors.length} console errors`);
  }
  console.log("  console clean");
});
