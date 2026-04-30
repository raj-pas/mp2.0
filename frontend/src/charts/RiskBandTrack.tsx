import { useTranslation } from "react-i18next";

import { BUCKET_COLORS, descriptorFor } from "../lib/risk";
import { cn } from "../lib/cn";

interface RiskBandTrackProps {
  /** Active canon-1-5 score (read-only marker). */
  score: 1 | 2 | 3 | 4 | 5 | null;
  /** Optional plan-baseline ghost marker (e.g. uncapped score before override). */
  baselineScore?: 1 | 2 | 3 | 4 | 5 | null;
  /** When true, renders a wider track for hero KPI cards. */
  size?: "sm" | "md";
}

const ALL_BANDS: (1 | 2 | 3 | 4 | 5)[] = [1, 2, 3, 4, 5];

/**
 * Read-only 5-band risk score marker (locked decision #6).
 *
 * Five segmented bands using canon-aligned colors; an `aria-valuemin/
 * valuemax/valuenow/valuetext` triple makes the marker accessible.
 *
 * R4 will wrap this in a permission-gated interactive RiskSlider with
 * keyboard-controlled band selection + override rationale.
 */
export function RiskBandTrack({ score, baselineScore = null, size = "md" }: RiskBandTrackProps) {
  const { t } = useTranslation();
  const descriptor = descriptorFor(score, t);
  const valueText = descriptor !== null ? `${descriptor} (${score} / 5)` : "—";
  const sizing =
    size === "sm"
      ? { row: "h-1.5", marker: "h-2.5", legend: "text-[8px]" }
      : { row: "h-2", marker: "h-3", legend: "text-[9px]" };

  return (
    <div
      role="meter"
      aria-valuemin={1}
      aria-valuemax={5}
      aria-valuenow={score ?? undefined}
      aria-valuetext={valueText}
      aria-label={t("routes.goal.risk_track_label")}
      className="flex flex-col gap-1"
    >
      <div
        className={cn("relative flex w-full overflow-hidden border border-hairline", sizing.row)}
      >
        {ALL_BANDS.map((band) => {
          const active = score === band;
          const baseline = baselineScore === band && score !== band;
          return (
            <div
              key={band}
              className={cn("flex-1 transition-opacity", !active && !baseline && "opacity-40")}
              style={{ background: BUCKET_COLORS[band] }}
              aria-hidden
            >
              {active && (
                <div
                  className={cn("border border-ink", sizing.marker)}
                  aria-hidden
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              )}
              {baseline && (
                <div
                  className={cn("border border-dashed border-ink/60", sizing.marker)}
                  aria-hidden
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              )}
            </div>
          );
        })}
      </div>
      <div
        className={cn(
          "flex justify-between font-mono uppercase tracking-widest text-muted",
          sizing.legend,
        )}
      >
        {ALL_BANDS.map((band) => (
          <span key={band}>{band}</span>
        ))}
      </div>
    </div>
  );
}
