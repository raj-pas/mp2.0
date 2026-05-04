/**
 * SourcePill — shared visual indicator for "is this surface showing
 * engine-canonical numbers, or calibration reference points?"
 *
 * Consumed by:
 *   - frontend/src/goal/GoalAllocationSection.tsx (Phase A2)
 *   - frontend/src/goal/MovesPanel.tsx (Phase A2)
 *   - frontend/src/goal/OptimizerOutputWidget.tsx (Phase A3)
 *
 * Per locked decisions §3.1 (slider-drag UX), §3.3 (Moves pill in scope),
 * §3.4 (copy: "Engine recommendation" / "Calibration preview"), §3.7
 * (parent-state-driven `isPreviewingOverride` boolean for drag mode).
 *
 * Three source variants:
 *   - "engine"           — engine `goal_rollup` consumed; ACCENT styling
 *   - "calibration"      — no engine rollup OR engine fallback; MUTED
 *   - "calibration_drag" — slider being dragged for what-if; MUTED + drag copy
 */
import { useTranslation } from "react-i18next";

export type PillSource = "engine" | "calibration" | "calibration_drag";

export interface SourcePillProps {
  source: PillSource;
  /** 8-char prefix shown when source === "engine"; null otherwise. */
  runSignature?: string | null;
}

export function SourcePill({ source, runSignature }: SourcePillProps) {
  const { t } = useTranslation();

  if (source === "engine") {
    return (
      <span
        role="status"
        aria-label={t("goal_allocation.from_run")}
        className="inline-flex items-center gap-1.5 bg-accent-2 text-paper px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest"
      >
        <span>{t("goal_allocation.from_run")}</span>
        {runSignature !== null && runSignature !== undefined && runSignature !== "" && (
          <span aria-hidden="true" className="opacity-75">
            · {runSignature.slice(0, 8)}
          </span>
        )}
      </span>
    );
  }

  // calibration + calibration_drag share visual; differ only in copy
  const copyKey =
    source === "calibration_drag"
      ? "goal_allocation.from_calibration_drag"
      : "goal_allocation.from_calibration";

  return (
    <span
      role="status"
      aria-label={t(copyKey)}
      className="inline-flex items-center gap-1.5 bg-paper-2 text-muted border border-hairline px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest"
    >
      {t(copyKey)}
    </span>
  );
}
