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
