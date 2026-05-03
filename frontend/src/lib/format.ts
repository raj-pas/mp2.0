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
