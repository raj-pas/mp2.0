/**
 * Goal page — hero KPIs + interactive RiskSlider + allocation +
 * optimizer output + rebalance moves + lognormal projection fan.
 *
 * Phase R4 ships every reading surface for the goal. The override
 * flow is canon-1-5 only (locked decision #6); save fires an
 * AuditEvent (locked decision #37) verified live during the deeper
 * smoke. The RiskSlider derivation breakdown is intentionally
 * disabled for R4 because the household-level anchor (Q1-Q4 → T/C
 * → anchor) is not yet exposed by `HouseholdDetailSerializer`;
 * locked decision #19 fixture regeneration in R7 unblocks it. The
 * slider still saves overrides correctly without the breakdown.
 */
import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { RiskBandTrack } from "../charts/RiskBandTrack";
import { Skeleton } from "../components/ui/skeleton";
import { RiskSlider } from "../components/ui/RiskSlider";
import { AdvisorSummaryPanel } from "../goal/AdvisorSummaryPanel";
import { GoalAllocationSection } from "../goal/GoalAllocationSection";
import { GoalProjectionsSection } from "../goal/GoalProjectionsSection";
import { MovesPanel } from "../goal/MovesPanel";
import { OptimizerOutputWidget } from "../goal/OptimizerOutputWidget";
import { RecommendationBanner } from "../goal/RecommendationBanner";
import { isAdvisorRole, useSession } from "../lib/auth";
import { type Goal, findGoal, useHousehold } from "../lib/household";
import { useOverrideHistory } from "../lib/preview";
import { formatCurrencyCAD } from "../lib/format";
import { descriptorFor, isCanonRisk } from "../lib/risk";

export function GoalRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { goalId } = useParams<{ goalId: string }>();
  const [rememberedId] = useRememberedClientId();
  const householdQuery = useHousehold(rememberedId);
  const session = useSession();
  const overridesQuery = useOverrideHistory(goalId ?? null);

  // Per locked §3.7: parent owns drag-preview state lifted from
  // RiskSlider via `onPreviewChange`. GoalAllocationSection + MovesPanel
  // both read this to flip their SourcePill to "calibration_drag" while
  // the slider is being dragged.
  const [isPreviewingOverride, setIsPreviewingOverride] = useState(false);

  if (rememberedId === null) {
    return (
      <main className="flex flex-1 items-center justify-center bg-paper">
        <p role="status" className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("routes.household.select_first")}
        </p>
      </main>
    );
  }

  if (householdQuery.isPending) {
    return (
      <main
        className="flex flex-1 flex-col gap-3 bg-paper p-5"
        aria-busy="true"
        aria-label={t("common.loading_route")}
      >
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
        <Skeleton className="h-32 w-full" />
      </main>
    );
  }

  if (householdQuery.isError) {
    return (
      <main
        role="alert"
        className="flex flex-1 flex-col items-center justify-center gap-3 bg-paper p-5"
      >
        <p className="font-sans text-[12px] font-semibold text-danger">
          {t("polish_a.goal.load_error_title")}
        </p>
        <button
          type="button"
          onClick={() => {
            void householdQuery.refetch();
          }}
          className="border border-hairline-2 bg-paper-2 px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-ink transition-colors hover:bg-paper motion-safe:transition-colors"
        >
          {t("polish_a.goal.retry")}
        </button>
      </main>
    );
  }

  const goal =
    goalId !== undefined && householdQuery.data ? findGoal(householdQuery.data, goalId) : null;
  if (goal === null || householdQuery.data === undefined) {
    return (
      <main className="flex flex-1 items-center justify-center bg-paper">
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("routes.goal.missing_goal")}
        </p>
      </main>
    );
  }

  const household = householdQuery.data;
  const horizonYears = computeHorizonYears(goal.target_date);
  const horizonText =
    horizonYears === null
      ? t("routes.goal.horizon_unset")
      : t("routes.goal.horizon_years", { count: horizonYears });
  const tier = tierForNecessity(goal.necessity_score);
  const tierText = tier !== null ? t(`routes.goal.tier_${tier}`) : null;
  const systemScore = isCanonRisk(goal.goal_risk_score) ? goal.goal_risk_score : null;

  const overrides = overridesQuery.data ?? [];
  const latestOverride = overrides.length > 0 ? (overrides[0] ?? null) : null;
  const effectiveScore =
    (latestOverride !== null && isCanonRisk(latestOverride.score_1_5)
      ? latestOverride.score_1_5
      : null) ?? systemScore;

  const descriptor = descriptorFor(effectiveScore, t);
  const role = session.data?.authenticated ? session.data.user.role : "";
  const canEdit = isAdvisorRole(role);

  return (
    <main className="flex flex-1 flex-col gap-3 overflow-y-auto bg-paper p-5">
      <header className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate("/")}
          className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-muted hover:text-ink"
        >
          <ChevronLeft aria-hidden className="h-3 w-3" />
          {t("routes.goal.back_to_household")}
        </button>
        <div className="text-right">
          <h2 className="font-serif text-2xl font-medium tracking-tight text-ink">{goal.name}</h2>
          {tierText !== null && (
            <p className="font-mono text-[10px] uppercase tracking-widest text-accent-2">
              {tierText}
            </p>
          )}
        </div>
      </header>

      <RecommendationBanner
        run={household.latest_portfolio_run}
        failure={household.latest_portfolio_failure}
        householdId={household.id}
      />

      <section
        className="grid grid-cols-4 gap-3 border border-hairline-2 bg-paper-2 px-5 py-4 shadow-sm"
        aria-label={t("routes.goal.kpi_target")}
      >
        <KpiTile
          label={t("routes.goal.kpi_target")}
          value={goal.target_amount !== null ? formatCurrencyCAD(goal.target_amount) : "—"}
        />
        <KpiTile
          label={t("routes.goal.kpi_funded")}
          value={formatCurrencyCAD(goal.current_funded_amount)}
        />
        <KpiTile label={t("routes.goal.kpi_horizon")} value={horizonText} />
        <KpiTile
          label={t("routes.goal.kpi_risk")}
          value={descriptor ?? t("routes.goal.kpi_risk_unset")}
          extra={
            <div className="mt-2 max-w-[200px]">
              <RiskBandTrack
                score={effectiveScore}
                baselineScore={
                  systemScore !== null && systemScore !== effectiveScore ? systemScore : null
                }
                size="sm"
              />
            </div>
          }
        />
      </section>

      {systemScore !== null && effectiveScore !== null && goalId !== undefined && (
        <RiskSlider
          goalId={goalId}
          systemScore={systemScore}
          effectiveScore={effectiveScore}
          isOverridden={latestOverride !== null}
          canEdit={canEdit}
          tier={tier}
          sizeShare={
            household.total_assets > 0 && goal.target_amount !== null
              ? Number(goal.target_amount) / household.total_assets
              : null
          }
          onPreviewChange={setIsPreviewingOverride}
        />
      )}

      {effectiveScore !== null && (
        <GoalAllocationSection
          goal={goal}
          household={household}
          effectiveScore={effectiveScore}
          isPreviewingOverride={isPreviewingOverride}
        />
      )}

      <AdvisorSummaryPanel household={household} goalId={goal.id} />

      <div className="grid grid-cols-2 gap-3">
        <OptimizerOutputWidget householdId={household.id} goalId={goal.id} />
        <MovesPanel
          householdId={household.id}
          goalId={goal.id}
          household={household}
          isPreviewingOverride={isPreviewingOverride}
        />
      </div>

      {effectiveScore !== null && horizonYears !== null && tier !== null && (
        <GoalProjectionsSection
          goal={goal}
          effectiveScore={effectiveScore}
          startValue={Number(goal.current_funded_amount || 0)}
          horizonYears={horizonYears}
          tier={tier}
        />
      )}

      <section className="border border-hairline-2 bg-paper p-4 shadow-sm">
        <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("routes.goal.linked_accounts_title")}
        </h3>
        <LinkedAccounts goal={goal} />
      </section>
    </main>
  );
}

function KpiTile({
  label,
  value,
  extra,
}: {
  label: string;
  value: string;
  extra?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</span>
      <span className="mt-1 font-serif text-lg font-medium text-ink">{value}</span>
      {extra}
    </div>
  );
}

function LinkedAccounts({ goal }: { goal: Goal }) {
  const { t } = useTranslation();
  const links = goal.account_allocations.filter((l) => Number(l.allocated_amount) > 0);
  if (links.length === 0) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("empty.no_holdings")}
      </p>
    );
  }
  return (
    <ul className="flex flex-col divide-y divide-hairline">
      {links.map((link) => (
        <li key={link.id}>
          <Link
            to={`/account/${encodeURIComponent(link.account_id)}`}
            className="flex items-baseline justify-between py-2 hover:bg-paper-2"
          >
            <span className="font-mono text-[10px] uppercase tracking-widest text-ink">
              {link.account_id}
            </span>
            <span className="font-mono text-[10px] text-accent-2">
              {formatCurrencyCAD(Number(link.allocated_amount))}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function computeHorizonYears(targetDate: string | null): number | null {
  if (targetDate === null || targetDate.length === 0) return null;
  const target = new Date(targetDate);
  if (Number.isNaN(target.getTime())) return null;
  const today = new Date();
  const diffMs = target.getTime() - today.getTime();
  const years = Math.round(diffMs / (1000 * 60 * 60 * 24 * 365.25));
  return Math.max(0, years);
}

function tierForNecessity(necessity: number | null): "need" | "want" | "wish" | "unsure" | null {
  if (necessity === null) return "unsure";
  if (necessity >= 4) return "need";
  if (necessity === 3) return "want";
  if (necessity >= 1) return "wish";
  return null;
}
