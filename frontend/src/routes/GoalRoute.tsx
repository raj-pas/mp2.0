import { ChevronLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { RiskBandTrack } from "../charts/RiskBandTrack";
import { Skeleton } from "../components/ui/skeleton";
import { type Goal, findGoal, useHousehold } from "../lib/household";
import { formatCad } from "../lib/format";
import { descriptorFor, isCanonRisk } from "../lib/risk";

export function GoalRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { goalId } = useParams<{ goalId: string }>();
  const [rememberedId] = useRememberedClientId();
  const householdQuery = useHousehold(rememberedId);

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
      <main className="flex flex-1 flex-col gap-3 bg-paper p-5">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-32 w-full" />
      </main>
    );
  }

  const goal =
    goalId !== undefined && householdQuery.data ? findGoal(householdQuery.data, goalId) : null;
  if (goal === null) {
    return (
      <main className="flex flex-1 items-center justify-center bg-paper">
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("routes.goal.missing_goal")}
        </p>
      </main>
    );
  }

  const horizonYears = computeHorizonYears(goal.target_date);
  const horizonText =
    horizonYears === null
      ? t("routes.goal.horizon_unset")
      : t("routes.goal.horizon_years", { count: horizonYears });
  const tierText = tierForNecessity(goal.necessity_score, t);
  const goalScore = isCanonRisk(goal.goal_risk_score) ? goal.goal_risk_score : null;
  const descriptor = descriptorFor(goal.goal_risk_score, t);

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

      <section
        className="grid grid-cols-4 gap-3 border border-hairline-2 bg-paper-2 px-5 py-4 shadow-sm"
        aria-label={t("routes.goal.kpi_target")}
      >
        <KpiTile
          label={t("routes.goal.kpi_target")}
          value={goal.target_amount !== null ? formatCad(goal.target_amount) : "—"}
        />
        <KpiTile
          label={t("routes.goal.kpi_funded")}
          value={formatCad(goal.current_funded_amount)}
        />
        <KpiTile label={t("routes.goal.kpi_horizon")} value={horizonText} />
        <KpiTile
          label={t("routes.goal.kpi_risk")}
          value={descriptor ?? t("routes.goal.kpi_risk_unset")}
          extra={
            <div className="mt-2 max-w-[200px]">
              <RiskBandTrack score={goalScore} size="sm" />
            </div>
          }
        />
      </section>

      <section className="grid grid-cols-2 gap-3">
        <div className="border border-hairline-2 bg-paper p-4 shadow-sm">
          <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("routes.goal.linked_accounts_title")}
          </h3>
          <LinkedAccounts goal={goal} />
        </div>
        <div className="border border-hairline-2 bg-paper p-4 shadow-sm">
          <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("routes.goal.blended_view_title")}
          </h3>
          <p className="text-[12px] leading-relaxed text-muted">
            {t("routes.goal.advanced_panels_pending")}
          </p>
        </div>
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
              {formatCad(Number(link.allocated_amount))}
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

function tierForNecessity(necessity: number | null, t: (key: string) => string): string | null {
  if (necessity === null) return t("routes.goal.tier_unsure");
  if (necessity >= 4) return t("routes.goal.tier_need");
  if (necessity === 3) return t("routes.goal.tier_want");
  if (necessity >= 1) return t("routes.goal.tier_wish");
  return null;
}
