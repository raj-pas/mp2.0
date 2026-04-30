/**
 * Fund-id naming canon + normalizer.
 *
 * The live data has four distinct conventions in flight (smoke
 * 2026-04-30). Locked decision #19 calls for Sandra/Mike fixture
 * regeneration in R7 to unify on the v36 universe; until then we
 * normalize defensively so chart palettes + display names work
 * regardless of source. Tracked as drift item #11.
 *
 * | Source                          | Format         | Example         |
 * |---------------------------------|----------------|-----------------|
 * | engine/sleeves.py (v36 canon)   | SH-Sav         | mixed-case      |
 * | Default CMA seed                | sh_savings     | snake_case      |
 * | Legacy persona Holding rows     | income_fund    | legacy product  |
 * | (deprecated) treemap.ts palette | sh-sav         | dashed lowercase|
 */

export type FundCanonId =
  | "SH-Sav"
  | "SH-Inc"
  | "SH-Eq"
  | "SH-Glb"
  | "SH-SC"
  | "SH-GSC"
  | "SH-Fnd"
  | "SH-Bld";

const CANON_IDS: FundCanonId[] = [
  "SH-Sav",
  "SH-Inc",
  "SH-Eq",
  "SH-Glb",
  "SH-SC",
  "SH-GSC",
  "SH-Fnd",
  "SH-Bld",
];

/**
 * Maps every observed identifier variant to its canon `SH-X` form.
 * Lowercased, so callers normalize the input first.
 */
const ALIAS_TO_CANON: Record<string, FundCanonId> = {
  // canon (mirror)
  "sh-sav": "SH-Sav",
  "sh-inc": "SH-Inc",
  "sh-eq": "SH-Eq",
  "sh-glb": "SH-Glb",
  "sh-sc": "SH-SC",
  "sh-gsc": "SH-GSC",
  "sh-fnd": "SH-Fnd",
  "sh-bld": "SH-Bld",
  // CMA seed snake_case
  sh_savings: "SH-Sav",
  sh_income: "SH-Inc",
  sh_equity: "SH-Eq",
  sh_global_equity: "SH-Glb",
  sh_small_cap_equity: "SH-SC",
  sh_global_small_cap_eq: "SH-GSC",
  sh_founders: "SH-Fnd",
  sh_builders: "SH-Bld",
  // Legacy persona Holding names (synthetic Sandra/Mike Chen seed)
  cash_savings: "SH-Sav",
  income_fund: "SH-Inc",
  equity_fund: "SH-Eq",
  global_equity_fund: "SH-Glb",
};

/**
 * Mirror of `engine/sleeves.SLEEVE_COLOR_HEX` keyed on canon `SH-X` ids.
 * Frontend duplication is intentional — locked decision #2 keeps math
 * server-side, but per-fund colors are display-only and shipping fonts
 * ship with the bundle.
 */
const FUND_COLOR_BY_CANON: Record<FundCanonId, string> = {
  "SH-Sav": "#5D7A8C", // slate
  "SH-Inc": "#2E4A6B", // navy
  "SH-Eq": "#0E1116", // ink
  "SH-Glb": "#8B5E3C", // copper
  "SH-SC": "#B87333", // orange
  "SH-GSC": "#2E5D3A", // green
  "SH-Fnd": "#6B5876", // plum
  "SH-Bld": "#8B8C5E", // olive
};

const FUND_NAME_BY_CANON: Record<FundCanonId, string> = {
  "SH-Sav": "Steadyhand Savings Fund",
  "SH-Inc": "Steadyhand Income Fund",
  "SH-Eq": "Steadyhand Equity Fund",
  "SH-Glb": "Steadyhand Global Equity Fund",
  "SH-SC": "Steadyhand Small-Cap Equity Fund",
  "SH-GSC": "Steadyhand Global Small-Cap Equity Fund",
  "SH-Fnd": "Steadyhand Founders Fund",
  "SH-Bld": "Steadyhand Builders Fund",
};

const FALLBACK_PALETTE = [
  "#5D7A8C",
  "#2E4A6B",
  "#8B5E3C",
  "#B87333",
  "#2E5D3A",
  "#6B5876",
  "#8B8C5E",
  "#6B8E8E",
];
const FALLBACK_FILL = "#9CA3AF";

/**
 * Resolve any observed fund-id variant to canon `SH-X` form.
 * Returns null if the id is unrecognized.
 */
export function canonizeFundId(rawId: string | null | undefined): FundCanonId | null {
  if (rawId === null || rawId === undefined) return null;
  const key = rawId.trim().toLowerCase().replace(/-/g, "_");
  // Direct hit on canon-as-key
  const dashedKey = rawId.trim().toLowerCase();
  return (
    ALIAS_TO_CANON[dashedKey] ??
    ALIAS_TO_CANON[key.replace(/_/g, "-")] ??
    ALIAS_TO_CANON[key] ??
    null
  );
}

export function fundColor(rawId: string | null | undefined, fallbackIndex = 0): string {
  const canon = canonizeFundId(rawId);
  if (canon !== null) return FUND_COLOR_BY_CANON[canon];
  return FALLBACK_PALETTE[fallbackIndex % FALLBACK_PALETTE.length] ?? FALLBACK_FILL;
}

export function fundDisplayName(rawId: string | null | undefined, fallback = ""): string {
  const canon = canonizeFundId(rawId);
  if (canon !== null) return FUND_NAME_BY_CANON[canon];
  return fallback;
}

export { CANON_IDS, FUND_COLOR_BY_CANON, FUND_NAME_BY_CANON };
