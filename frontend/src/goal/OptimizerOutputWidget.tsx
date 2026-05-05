/**
 * Optimizer-output widget — engine-first improvement % consumption with
 * calibration fallback + slider-drag UX (Phase A3 / locked §3.1, §3.5).
 *
 * Source-decision tree (mirror GoalAllocationSection per locked §3.7):
 *   - `isPreviewingOverride === true` (slider dragged for what-if):
 *       → calibration_drag pill; improvement_pct from `useOptimizerOutput`
 *   - `link_recommendations[goal_id].length > 0` AND not dragging:
 *       → engine pill with run signature; improvement_pct = dollar-weighted
 *         engine `idealReturn - currentReturn` per locked §3.5
 *   - Otherwise (no engine links, no drag):
 *       → calibration pill; improvement_pct from `useOptimizerOutput`
 *
 * Engine-path math (per locked §3.5 + plan §A3):
 *   idealReturn   = Σ (link.expected_return × link.allocated_amount) / Σ link.allocated_amount
 *   currentReturn = Σ (link.current_comparison?.expected_return ?? link.expected_return) ×
 *                     link.allocated_amount / Σ link.allocated_amount
 *   improvement_pct = (idealReturn - currentReturn) × 100   // ← backend ships pct-scale
 *
 * `current_comparison.expected_return` is `number | null` per the engine
 * contract (household.ts:91-100); the null-guard falls back to the engine's
 * own `expected_return` so the comparison degenerates to "no improvement"
 * rather than NaN-ing the blend.
 *
 * Calibration's `effective_descriptor`, `ideal_low`, `current_low` remain
 * canonical even on engine path (the descriptor reflects the same canon
 * 1-5 scale the engine uses; the dollar bands have no clean engine
 * analogue). The SourcePill signals which source the headline
 * `improvement_pct` comes from — the most prominent (accent-toned) stat.
 */
import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { findGoalLinkRecommendations, type HouseholdDetail } from "../lib/household";
import { useOptimizerOutput } from "../lib/preview";
import { formatCadCompact, formatPct } from "../lib/format";
import { SourcePill, type PillSource } from "./SourcePill";

interface OptimizerOutputWidgetProps {
  householdId: string;
  goalId: string;
  household: HouseholdDetail;
  /**
   * True when the advisor is dragging the risk slider but hasn't yet saved
   * the override. Per locked §3.1: in this state, improvement_pct tracks
   * the slider via calibration (live what-if), not the engine (which is
   * fixed to the saved goal config).
   */
  isPreviewingOverride?: boolean;
}

export function OptimizerOutputWidget({
  householdId,
  goalId,
  household,
  isPreviewingOverride = false,
}: OptimizerOutputWidgetProps) {
  const { t } = useTranslation();

  // Always call useOptimizerOutput so the calibration query is ready when
  // we need it for descriptor/dollar tiles (no conditional hooks).
  const calibration = useOptimizerOutput(householdId, goalId);

  const links = findGoalLinkRecommendations(household, goalId);
  const useEnginePath = links.length > 0 && !isPreviewingOverride;
  const source: PillSource = isPreviewingOverride
    ? "calibration_drag"
    : links.length > 0
      ? "engine"
      : "calibration";
  const runSignature = household.latest_portfolio_run?.run_signature ?? null;

  if (calibration.isPending) {
    return (
      <Section
        title={t("optimizer_output.section_title")}
        pill={<SourcePill source={source} runSignature={runSignature} />}
      >
        <Skeleton className="h-12 w-full" />
      </Section>
    );
  }
  if (calibration.isError || calibration.data === undefined) {
    return (
      <Section
        title={t("optimizer_output.section_title")}
        pill={<SourcePill source={source} runSignature={runSignature} />}
      >
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("errors.preview_failed")}
        </p>
      </Section>
    );
  }

  const calData = calibration.data;
  const pUsedPct = (calData.p_used * 100).toFixed(0);

  const improvementPct = useEnginePath
    ? engineImprovementPct(links) ?? calData.improvement_pct
    : calData.improvement_pct;

  return (
    <Section
      title={t("optimizer_output.section_title")}
      pill={<SourcePill source={source} runSignature={runSignature} />}
    >
      <div className="grid grid-cols-2 gap-4">
        <Stat
          label={t("optimizer_output.improvement_pct", { p: pUsedPct })}
          primary={formatPct(improvementPct, 1)}
          tone="accent"
        />
        <Stat
          label={t("optimizer_output.effective_score")}
          primary={calData.effective_descriptor}
          secondary={`${calData.effective_score_1_5} / 5 · ${t(`routes.goal.tier_${calData.tier}`)}`}
        />
        <Stat
          label={t("optimizer_output.ideal_label", { p: pUsedPct })}
          primary={formatCadCompact(calData.ideal_low)}
        />
        <Stat
          label={t("optimizer_output.current_label", { p: pUsedPct })}
          primary={formatCadCompact(calData.current_low)}
        />
      </div>
    </Section>
  );
}

/**
 * Dollar-weighted engine improvement: idealReturn - currentReturn across
 * all link_recommendations for a goal. Returns null if total allocated
 * amount is non-positive (degenerate case — caller falls back to
 * calibration improvement_pct).
 */
function engineImprovementPct(
  links: ReturnType<typeof findGoalLinkRecommendations>,
): number | null {
  const totalAllocated = links.reduce((s, l) => s + Number(l.allocated_amount || 0), 0);
  if (totalAllocated <= 0) return null;

  const idealReturn =
    links.reduce((s, l) => s + Number(l.expected_return) * Number(l.allocated_amount || 0), 0) /
    totalAllocated;
  const currentReturn =
    links.reduce((s, l) => {
      const cur = l.current_comparison?.expected_return ?? l.expected_return;
      return s + Number(cur) * Number(l.allocated_amount || 0);
    }, 0) / totalAllocated;
  // Multiply by 100 to match the backend `improvement_pct` contract (pct-scale,
  // not 0..1) — see web/api/preview_views.py:476.
  return (idealReturn - currentReturn) * 100;
}

function Section({
  title,
  children,
  pill,
}: {
  title: string;
  children: React.ReactNode;
  pill?: React.ReactNode;
}) {
  return (
    <section className="border border-hairline-2 bg-paper p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between gap-2">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">{title}</h3>
        {pill !== undefined && pill !== null && pill}
      </header>
      {children}
    </section>
  );
}

function Stat({
  label,
  primary,
  secondary,
  tone = "default",
}: {
  label: string;
  primary: string;
  secondary?: string;
  tone?: "default" | "accent";
}) {
  const primaryClass =
    tone === "accent"
      ? "font-serif text-2xl font-medium text-accent-2"
      : "font-serif text-lg font-medium text-ink";
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</span>
      <span className={primaryClass}>{primary}</span>
      {secondary !== undefined && (
        <span className="font-mono text-[10px] text-muted">{secondary}</span>
      )}
    </div>
  );
}
