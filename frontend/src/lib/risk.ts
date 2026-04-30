import { type TFunction } from "i18next";

/**
 * Canonical risk-score helpers (locked decision #5).
 *
 * Score 1-5 ↔ canon descriptor:
 *   1 → Cautious
 *   2 → Conservative-balanced
 *   3 → Balanced
 *   4 → Balanced-growth
 *   5 → Growth-oriented
 *
 * The mockup's retired labels (Conservative / Cautious / Balanced /
 * Balanced Growth / Growth) are explicitly NOT used.
 */
export const RISK_DESCRIPTOR_KEYS: Record<1 | 2 | 3 | 4 | 5, string> = {
  1: "risk_descriptors.1",
  2: "risk_descriptors.2",
  3: "risk_descriptors.3",
  4: "risk_descriptors.4",
  5: "risk_descriptors.5",
};

export const BUCKET_COLORS: Record<1 | 2 | 3 | 4 | 5, string> = {
  1: "#5D7A8C", // Cautious
  2: "#6B8E8E", // Conservative-balanced
  3: "#C5A572", // Balanced
  4: "#B87333", // Balanced-growth
  5: "#8B2E2E", // Growth-oriented
};

export function isCanonRisk(value: number | null | undefined): value is 1 | 2 | 3 | 4 | 5 {
  return value === 1 || value === 2 || value === 3 || value === 4 || value === 5;
}

export function descriptorFor(score: number | null | undefined, t: TFunction): string | null {
  if (!isCanonRisk(score)) return null;
  return t(RISK_DESCRIPTOR_KEYS[score]);
}
