import { formatPct } from "../lib/format";
import { cn } from "../lib/cn";

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
}

/**
 * Horizontal "top X by %" bars. Used for top-funds and asset-class
 * breakdowns in the AccountRoute portfolio-stats panel.
 *
 * Pure CSS / Tailwind (no Chart.js needed) — keeps the chart bundle
 * tight and lets the hairline aesthetic match other paper surfaces.
 */
export function AllocationBars({ rows, limit, ariaLabel }: AllocationBarsProps) {
  const visible = limit !== undefined ? rows.slice(0, limit) : rows;
  if (visible.length === 0) {
    return <p className="font-mono text-[10px] uppercase tracking-widest text-muted">—</p>;
  }
  return (
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
  );
}
