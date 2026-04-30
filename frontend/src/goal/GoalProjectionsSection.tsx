/**
 * Goal projections panel: lognormal fan chart + side metrics.
 *
 * Driven by `/api/preview/projection-paths/` for the band data,
 * `/api/preview/projection/` for the headline percentile metrics,
 * and `/api/preview/probability/` for the target-probability badge
 * (when a target_amount is set on the goal).
 */
import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { FanChart } from "../charts/FanChart";
import { type Goal } from "../lib/household";
import { type Tier, useProbability, useProjection, useProjectionPaths } from "../lib/preview";
import { formatCadCompact } from "../lib/format";

interface GoalProjectionsSectionProps {
  goal: Goal;
  effectiveScore: 1 | 2 | 3 | 4 | 5;
  /** Funded amount serves as the projection start. */
  startValue: number;
  horizonYears: number;
  tier: Tier;
}

export function GoalProjectionsSection({
  goal,
  effectiveScore,
  startValue,
  horizonYears,
  tier,
}: GoalProjectionsSectionProps) {
  const { t } = useTranslation();
  const enabled = startValue > 0 && horizonYears > 0;

  const projection = useProjection(
    enabled
      ? {
          start: startValue,
          score_1_5: effectiveScore,
          horizon_years: horizonYears,
          mode: "current",
          tier,
        }
      : null,
  );

  const projectionPaths = useProjectionPaths(
    enabled
      ? {
          start: startValue,
          score_1_5: effectiveScore,
          horizon_years: horizonYears,
          percentiles: [0.1, 0.25, 0.5, 0.75, 0.9],
          n_steps: Math.min(60, Math.max(8, Math.floor(horizonYears * 4))),
          mode: "current",
        }
      : null,
  );

  const probability = useProbability(
    enabled && goal.target_amount !== null && goal.target_amount > 0
      ? {
          start: startValue,
          score_1_5: effectiveScore,
          horizon_years: horizonYears,
          target: Number(goal.target_amount),
          mode: "current",
        }
      : null,
  );

  if (!enabled) {
    return (
      <Section title={t("fan_chart.title")}>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("fan_chart.no_data")}
        </p>
      </Section>
    );
  }

  return (
    <Section title={t("fan_chart.title")}>
      <div className="grid grid-cols-[1fr_240px] gap-4">
        <div className="h-72">
          {projectionPaths.isPending ? (
            <Skeleton className="h-full w-full" />
          ) : projectionPaths.isSuccess ? (
            <FanChart
              paths={projectionPaths.data.paths}
              targetValue={goal.target_amount !== null ? Number(goal.target_amount) : null}
              probabilityAtTarget={probability.data?.probability ?? null}
              ariaLabel={t("fan_chart.aria_label")}
              tierLabel={t(`routes.goal.tier_${tier}`)}
            />
          ) : (
            <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
              {t("errors.preview_failed")}
            </p>
          )}
        </div>
        <aside className="flex flex-col gap-3">
          {projection.isPending ? (
            <Skeleton className="h-32 w-full" />
          ) : projection.isSuccess ? (
            <>
              <Stat
                label={t("fan_chart.median_label_p50")}
                value={formatCadCompact(projection.data.p50)}
              />
              <Stat
                label={t("fan_chart.upper_label")}
                value={formatCadCompact(projection.data.p90)}
              />
              <Stat
                label={t("fan_chart.lower_label")}
                value={formatCadCompact(projection.data.p10)}
              />
            </>
          ) : (
            <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
              {t("errors.preview_failed")}
            </p>
          )}
        </aside>
      </div>
    </Section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</span>
      <span className="font-serif text-lg font-medium text-ink">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border border-hairline-2 bg-paper p-4 shadow-sm">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">{title}</h3>
      {children}
    </section>
  );
}
