import { expect, test } from "@playwright/test";
import { readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";

const bundleRoot = process.env.MP20_REAL_BUNDLE_ROOT;
const artifactRoot = process.env.PLAYWRIGHT_OUTPUT_DIR;

const bundles = bundleRoot ? realBundles(bundleRoot) : [];

if (!bundleRoot || !artifactRoot || !bundles.length) {
  test("real bundle regression configuration", async () => {
    test.skip(!bundleRoot, "Set MP20_REAL_BUNDLE_ROOT to run local real-bundle regression.");
    test.skip(
      !artifactRoot,
      "Set PLAYWRIGHT_OUTPUT_DIR under MP20_SECURE_DATA_ROOT for real artifacts.",
    );
    test.skip(!bundles.length, "No supported bundle files were found.");
  });
} else {
  for (const [index, files] of bundles.entries()) {
    test(`real bundle ${index + 1} uploads and exposes review state`, async ({ page }) => {
    test.setTimeout(10 * 60_000);
    const email = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
    const password = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";
    const workspaceLabel = `Real Regression Bundle ${index + 1} ${Date.now()}`;

    await page.goto("/");
    await page.getByPlaceholder("Email").fill(email);
    await page.getByPlaceholder("Password").fill(password);
    await page.getByRole("button", { name: /Sign In/i }).click();
    await expect(page.getByText(email)).toBeVisible();

    await page.getByRole("button", { name: "Review" }).click();
    await page.getByPlaceholder("Household or bundle label").fill(workspaceLabel);
    await page.getByRole("button", { name: /Create Workspace/i }).click();
    await expect(page.getByRole("button", { name: new RegExp(workspaceLabel) })).toBeVisible();

    await page.locator('input[type="file"]').setInputFiles(files);
    await page.getByRole("button", { name: /Upload Files/i }).click();
    await expect(page.getByText(/Uploaded /i)).toBeVisible();
    await expect(page.getByText(/Documents/i)).toBeVisible();
    await expect(page.getByText(/Worker health/i)).toBeVisible();
    await expect(page.getByText(/Readiness/i)).toBeVisible();
    });
  }
}

function realBundles(root: string): string[][] {
  const resolvedRoot = resolve(root);
  const entries = readdirSync(resolvedRoot, { withFileTypes: true });
  const directories = entries.filter((entry) => entry.isDirectory());
  if (!directories.length) {
    return [filesInDirectory(resolvedRoot)];
  }
  return directories.map((directory) => filesInDirectory(resolve(resolvedRoot, directory.name)));
}

function filesInDirectory(directory: string): string[] {
  return readdirSync(directory)
    .map((name) => resolve(directory, name))
    .filter((path) => statSync(path).isFile())
    .filter((path) => /\.(pdf|docx|xlsx|csv|txt|md|png|jpe?g|tiff?)$/i.test(path));
}
