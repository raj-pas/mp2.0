/**
 * CAD currency + percent formatters used across the v36 surfaces.
 *
 * Mockup discipline:
 *   - JetBrains Mono numerals for advisor-facing $/% displays.
 *   - $1.92M / $847K compact form for topbar AUM badge.
 *   - Full $1,920,000 form for ledger / per-goal summaries.
 *   - Percentages without trailing zeroes by default; pass digits to override.
 */

const CAD = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
  maximumFractionDigits: 0,
});

const CAD_COMPACT = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
  notation: "compact",
  maximumFractionDigits: 2,
});

export function formatCad(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return CAD.format(value);
}

export function formatCadCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return CAD_COMPACT.format(value);
}

export function formatPct(
  value: number | null | undefined,
  digits = 1,
  { multiply100 = false }: { multiply100?: boolean } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const pct = multiply100 ? value * 100 : value;
  return `${pct.toFixed(digits)}%`;
}

/**
 * Tier-3 polish helper (production-quality-bar §1.4): canonical CAD
 * currency formatter. Mirrors `formatCad` but exposed under the name
 * called for in the polish spec so future surfaces can adopt it
 * without aliasing. Returns the raw `Intl.NumberFormat("en-CA", …)`
 * output (e.g. `$1,234,567`); the empty-value sentinel still goes
 * through the same `—` path.
 */
export function formatCurrencyCAD(value: number | null | undefined): string {
  return formatCad(value);
}

const DATE_LONG = new Intl.DateTimeFormat("en-CA", { dateStyle: "long" });

/**
 * Tier-3 polish helper (production-quality-bar §1.4): canonical
 * en-CA long-form date formatter (e.g. "May 3, 2026"). Accepts ISO
 * strings or Date instances; returns "—" for nullish or invalid
 * inputs so consumers don't have to guard.
 */
export function formatDateLong(value: string | Date | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return DATE_LONG.format(date);
}

// ---------------------------------------------------------------------------
// P6 — Fund → asset-class aggregation helpers (plan v20 §A1.35 / G8).
// ---------------------------------------------------------------------------
//
// In `asset_class` mode, the AccountRoute / GoalRoute AllocationBars panel
// aggregates fund-level rows up to coarser asset-class buckets. The mapping
// mirrors `engine/fixtures/default_cma_v1.json::funds[].asset_class_weights`
// — the canonical CMA fund universe for the limited-beta pilot. When a
// fund-id can't be resolved (e.g. external transfer-in funds, post-pilot
// CMA expansion), the helper marks the row `lowConfidence: true` so the
// rendering layer can display a chip per the §A1.35 fallback contract.
//
// We intentionally keep this metadata on the frontend (not via API) — the
// fund universe is small (8 SH funds), churns slowly, and the data is
// public-domain CMA assumptions. Locked decision #2 (engine-only math) is
// preserved because aggregation is a pure display projection (sum of
// weights × known fund weights), not optimization.

import { canonizeFundId } from "./funds";

export type AssetClassId = "cash" | "fixed_income" | "equity" | "real_assets";

/**
 * Coarse asset-class display labels (mirrors canon vocab). UI keys these
 * via i18n where possible; this map is the fallback when no translation
 * is wired (e.g. tests, Methodology overlay).
 */
export const ASSET_CLASS_LABEL: Record<AssetClassId, string> = {
  cash: "Cash",
  fixed_income: "Fixed Income",
  equity: "Equity",
  real_assets: "Real Assets",
};

export const ASSET_CLASS_COLOR: Record<AssetClassId, string> = {
  cash: "#9CA3AF",
  fixed_income: "#6B8E8E",
  equity: "#2E4A6B",
  real_assets: "#6B5876",
};

/**
 * Fund-id → asset-class breakdown (sums to 1.0 per row). Mirrors
 * `engine/fixtures/default_cma_v1.json` as of 2026-05-04. Keyed on
 * canon `SH-X` ids (post-canonizeFundId normalization).
 */
const FUND_ASSET_CLASS_BREAKDOWN: Record<string, Partial<Record<AssetClassId, number>>> = {
  "SH-Sav": { cash: 1.0 },
  "SH-Inc": { cash: 0.05, fixed_income: 0.75, equity: 0.2 },
  "SH-Eq": { equity: 1.0 },
  "SH-Glb": { equity: 1.0 },
  "SH-SC": { equity: 1.0 },
  "SH-GSC": { equity: 1.0 },
  "SH-Fnd": { cash: 0.05, fixed_income: 0.4, equity: 0.55 },
  "SH-Bld": { cash: 0.02, fixed_income: 0.18, equity: 0.8 },
};

/**
 * Per-fund row consumed by `aggregateByAssetClass`. Mirrors the shape
 * AccountRoute already builds for `<AllocationBars>` (id + label + pct).
 * `pct` is a 0..1 fraction (matching `Holding.weight`).
 */
export interface AggregatableFundRow {
  id: string;
  pct: number;
}

export interface AssetClassAllocation {
  id: string;
  label: string;
  pct: number;
  color: string;
  /**
   * True when at least one source fund could not be mapped to an
   * asset-class breakdown (unknown fund-id). The UI renders a
   * "low confidence" chip + falls back to fund-only mode for that row.
   */
  lowConfidence: boolean;
}

/**
 * Aggregate per-fund rows into asset-class buckets. Returns one row per
 * non-zero asset class, sorted by `pct` desc. When any fund-id is
 * unrecognized, the row carrying the residual is flagged `lowConfidence`
 * — the call-site can promote that signal to a chip.
 *
 * Math: for each fund row, distribute its pct into the configured
 * asset-class breakdown (defaults to 100% to a synthetic "unknown"
 * bucket when the breakdown is missing — but we represent that as a
 * lowConfidence flag rather than an extra bucket so the chart stays
 * clean).
 */
export function aggregateByAssetClass(rows: AggregatableFundRow[]): AssetClassAllocation[] {
  const byClass = new Map<AssetClassId, number>();
  let unmappedPct = 0;
  for (const row of rows) {
    const canon = canonizeFundId(row.id);
    const breakdown = canon !== null ? FUND_ASSET_CLASS_BREAKDOWN[canon] : undefined;
    if (breakdown === undefined) {
      unmappedPct += row.pct;
      continue;
    }
    for (const [klass, weight] of Object.entries(breakdown) as [AssetClassId, number][]) {
      byClass.set(klass, (byClass.get(klass) ?? 0) + row.pct * weight);
    }
  }
  const result: AssetClassAllocation[] = [];
  for (const [klass, pct] of byClass) {
    if (pct <= 0) continue;
    result.push({
      id: klass,
      label: ASSET_CLASS_LABEL[klass],
      pct,
      color: ASSET_CLASS_COLOR[klass],
      lowConfidence: false,
    });
  }
  if (unmappedPct > 0) {
    // Surface the unmapped portion as a synthetic "Unclassified" row so
    // bar totals stay honest. The chip lives on the row itself; the
    // component layer can also render a global chip in the same panel.
    result.push({
      id: "unclassified",
      label: "Unclassified",
      pct: unmappedPct,
      color: "#B87333",
      lowConfidence: true,
    });
  }
  result.sort((a, b) => b.pct - a.pct);
  return result;
}
