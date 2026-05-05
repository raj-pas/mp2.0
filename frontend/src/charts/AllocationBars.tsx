import { useTranslation } from "react-i18next";

import { aggregateByAssetClass, formatPct } from "../lib/format";
import { cn } from "../lib/cn";
import type { FundAssetMode } from "../chrome/ToggleFundAssetClass";

export type AllocationRow = {
  id: string;
  label: string;
  pct: number;
  color: string;
};

interface AllocationBarsProps {
  rows: AllocationRow[];
  /** Optional cap; rows beyond cap are dropped. */
  limit?: number;
  /** Aria label for the bar list. */
  ariaLabel?: string;
  /**
   * P6 (plan v20 §A1.35): `'fund'` (default) renders the rows as-is;
   * `'asset_class'` aggregates rows up to coarser asset-class buckets
   * via fund metadata. Falls back to fund-only with a low-confidence
   * chip when any source fund is unmapped.
   */
  mode?: FundAssetMode;
}

/**
 * Horizontal "top X by %" bars. Used for top-funds and asset-class
 * breakdowns in the AccountRoute portfolio-stats panel.
 *
 * Pure CSS / Tailwind (no Chart.js needed) — keeps the chart bundle
 * tight and lets the hairline aesthetic match other paper surfaces.
 */
export function AllocationBars({ rows, limit, ariaLabel, mode = "fund" }: AllocationBarsProps) {
  const { t } = useTranslation();
  const aggregated =
    mode === "asset_class"
      ? aggregateByAssetClass(rows.map((r) => ({ id: r.id, pct: r.pct })))
      : null;
  const lowConfidence = aggregated?.some((r) => r.lowConfidence) ?? false;
  const visibleRows: AllocationRow[] =
    aggregated !== null
      ? aggregated.map((r) => ({ id: r.id, label: r.label, pct: r.pct, color: r.color }))
      : rows;
  const visible = limit !== undefined ? visibleRows.slice(0, limit) : visibleRows;
  if (visible.length === 0) {
    return <p className="font-mono text-[10px] uppercase tracking-widest text-muted">—</p>;
  }
  return (
    <div className="flex flex-col gap-1.5">
      {mode === "asset_class" && lowConfidence && (
        <p
          data-testid="allocation-bars-low-confidence"
          className="font-mono text-[9px] uppercase tracking-widest text-accent-2"
        >
          {t("allocation_bars.low_confidence")}
        </p>
      )}
      <ul aria-label={ariaLabel} className="flex flex-col gap-1.5">
        {visible.map((row) => (
          <li key={row.id} className="flex items-center gap-2">
            <span className="w-32 truncate font-sans text-[11px] text-ink">{row.label}</span>
            <span
              className={cn(
                "h-2 flex-1 overflow-hidden border border-hairline bg-paper-2",
                "[&>span]:block [&>span]:h-full",
              )}
            >
              <span
                style={{
                  width: `${Math.min(100, Math.max(0, row.pct * 100))}%`,
                  background: row.color,
                }}
              />
            </span>
            <span className="w-12 text-right font-mono text-[10px] text-ink">
              {formatPct(row.pct, 1, { multiply100: true })}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
