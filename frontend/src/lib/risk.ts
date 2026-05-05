import { type TFunction } from "i18next";

import {
  type CanonRiskScore,
  CANON_RISK_PERCENTILE,
} from "./schemas";

/**
 * Canonical risk-score helpers (locked decision #5 + canon §11.4).
 *
 * Score 1-5 ↔ canon descriptor:
 *   1 → Cautious
 *   2 → Conservative-balanced
 *   3 → Balanced
 *   4 → Balanced-growth
 *   5 → Growth-oriented
 *
 * The mockup's retired labels (Conservative / Cautious / Balanced /
 * Balanced Growth / Growth) are explicitly NOT used. The descriptor
 * literals themselves live in `lib/schemas.ts`
 * (`CANON_RISK_DESCRIPTORS`); this module is the i18n-aware façade.
 *
 * P5 (plan v20 §A1.34): Wizard + Review consume the same helper so
 * the descriptor string + 1-5 ↔ percentile mapping cannot drift
 * across surfaces.
 */
export const RISK_DESCRIPTOR_KEYS: Record<CanonRiskScore, string> = {
  1: "risk_descriptors.1",
  2: "risk_descriptors.2",
  3: "risk_descriptors.3",
  4: "risk_descriptors.4",
  5: "risk_descriptors.5",
};

export const BUCKET_COLORS: Record<CanonRiskScore, string> = {
  1: "#5D7A8C", // Cautious
  2: "#6B8E8E", // Conservative-balanced
  3: "#C5A572", // Balanced
  4: "#B87333", // Balanced-growth
  5: "#8B2E2E", // Growth-oriented
};

export function isCanonRisk(value: number | null | undefined): value is CanonRiskScore {
  return value === 1 || value === 2 || value === 3 || value === 4 || value === 5;
}

export function descriptorFor(
  score: number | null | undefined,
  t: TFunction,
): string | null {
  if (!isCanonRisk(score)) return null;
  return t(RISK_DESCRIPTOR_KEYS[score]);
}

/**
 * Canon §11.4 1-5 → frontier-percentile mapping (5/15/25/35/45).
 *
 * Mirrors `engine/projections.py::BUCKET_REPRESENTATIVE_SCORE`. The
 * mapping flows through `web/api/preview_views.py` to frontend
 * surfaces; both Wizard preview and Review goal/household summary
 * cards consume this helper to display "your goal optimizes the Nth
 * percentile outcome on the active frontier."
 *
 * Returns `null` for non-canon input (matches `descriptorFor`'s
 * permissive null-passthrough so callers can treat both helpers
 * uniformly).
 */
export function scoreToPercentile(
  score: number | null | undefined,
): number | null {
  if (!isCanonRisk(score)) return null;
  return CANON_RISK_PERCENTILE[score];
}
