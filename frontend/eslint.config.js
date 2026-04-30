// ESLint flat config (locked decision #22e + #28a).
// - TypeScript strict + zero `any`
// - React hooks
// - jsx-a11y baseline (WCAG 2.1 AA per locked decision #12)
// - i18next/no-literal-string for user-visible strings (locked decision #28a)
// - Prettier compatibility (turn off rules Prettier handles)
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import i18next from "eslint-plugin-i18next";
import prettierConfig from "eslint-config-prettier";
import globals from "globals";

export default tseslint.config(
  {
    ignores: ["dist", "node_modules", "playwright-report", "test-results", "e2e"],
  },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: { ...globals.browser, ...globals.es2020 },
    },
    plugins: {
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      i18next,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.flatConfigs.recommended.rules,
      // i18n discipline (locked decision #28a)
      "i18next/no-literal-string": [
        "error",
        {
          markupOnly: true,
          ignoreAttribute: ["data-testid", "aria-label", "id", "name", "type", "role"],
        },
      ],
      // TS strict + zero any (locked decision #22a)
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  // i18n keys are objects in JSON; rule doesn't apply to JSON imports.
  // Tests get jsx-a11y but not i18n literal-string rule (component tests
  // use literal strings in assertions).
  {
    files: ["src/**/*.test.{ts,tsx}", "src/**/__tests__/**/*.{ts,tsx}"],
    rules: {
      "i18next/no-literal-string": "off",
    },
  },
  prettierConfig,
);
