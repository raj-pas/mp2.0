/**
 * Vitest configuration (Phase 6 scaffolding — sub-session #3).
 *
 * Powers `npm run test:unit`. Uses the same vite plugin chain as
 * `vite.config.ts` so React/TS resolution mirrors the production
 * build. jsdom environment + jest-dom matchers for React component
 * tests.
 *
 * Excludes:
 *   - `e2e/**` Playwright specs (those use playwright.config.ts).
 *   - `dist/` + `node_modules/`.
 *
 * Coverage opt-in via `npm run test:unit -- --coverage`. Phase 6
 * adds the 100%-on-new-code gate via `.coveragerc` equivalent in
 * v8 coverage config (vitest.coverage).
 */
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", "dist", "e2e"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "json"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/test/**",
        "src/**/*.test.{ts,tsx}",
        "src/**/*.spec.{ts,tsx}",
        "src/lib/api-types.ts",
        "src/main.tsx",
      ],
    },
  },
});
