/**
 * Vitest setup (Phase 6 scaffolding — sub-session #3).
 *
 * - Loads jest-dom matchers (toBeInTheDocument, toHaveClass, …).
 * - Mocks i18next so `useTranslation()` returns identity-keyed
 *   translations in unit tests (cleaner assertions than wiring up
 *   the full namespace).
 * - Resets fetch mock between tests.
 */
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// Cleanup after each test prevents DOM bleed between specs.
afterEach(() => {
  cleanup();
});

// react-i18next mock: `useTranslation` returns the key itself so
// assertions can target the i18n key directly (e.g.,
// `getByText("doc_detail.add_save")`). Components remain unchanged.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (
        options !== undefined &&
        typeof options === "object" &&
        "defaultValue" in options
      ) {
        return String(options.defaultValue);
      }
      return key;
    },
    i18n: {
      changeLanguage: vi.fn(),
    },
  }),
  Trans: ({ children }: { children?: React.ReactNode }) => children ?? null,
  initReactI18next: { type: "3rdParty", init: vi.fn() },
}));
