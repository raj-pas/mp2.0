/**
 * i18n scaffolding (locked decision #12).
 *
 * v1 ships English-only; French translations land later. The locale
 * switcher is feature-flagged off (no UI surface yet); all user-visible
 * strings flow through `t()` so adding fr-CA is a translation-file edit.
 *
 * The ESLint rule `i18next/no-literal-string` (locked decision #28a)
 * enforces every UI string flows through this scaffold.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import fr from "./fr.json";

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  // v1: locale switcher feature-flagged off; locked decision #12.
  // Multi-device / per-user persistence is Phase B (locked decision #32c).
});

export default i18n;
