import { ChevronLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { AllocationBars, type AllocationRow } from "../charts/AllocationBars";
import { RingChart, type RingDatum } from "../charts/RingChart";
import { Skeleton } from "../components/ui/skeleton";
import { findAccount, type Holding, useHousehold } from "../lib/household";
import { formatCad, formatCadCompact } from "../lib/format";

const FUND_COLORS: Record<string, string> = {
  "sh-sav": "#5D7A8C",
  "sh-inc": "#2E4A6B",
  "sh-eq": "#0E1116",
  "sh-glb": "#8B5E3C",
  "sh-sc": "#B87333",
  "sh-gsc": "#2E5D3A",
  "sh-fnd": "#6B5876",
  "sh-bld": "#8B8C5E",
};
const FALLBACK_PALETTE = ["#5D7A8C", "#2E4A6B", "#8B5E3C", "#B87333", "#2E5D3A", "#6B5876"];

function colorForFund(sleeveId: string, fallbackIndex: number): string {
  return (
    FUND_COLORS[sleeveId] ?? FALLBACK_PALETTE[fallbackIndex % FALLBACK_PALETTE.length] ?? "#9CA3AF"
  );
}

export function AccountRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { accountId } = useParams<{ accountId: string }>();
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
        <Skeleton className="h-64 w-full" />
      </main>
    );
  }

  const account =
    accountId !== undefined && householdQuery.data
      ? findAccount(householdQuery.data, accountId)
      : null;
  if (account === null) {
    return (
      <main className="flex flex-1 items-center justify-center bg-paper">
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("routes.account.missing_account")}
        </p>
      </main>
    );
  }

  const holdings = account.holdings.slice().sort((a, b) => b.weight - a.weight);
  const ringData = buildRingData(holdings);
  const barRows = buildBarRows(holdings);
  const goalsInAccount =
    householdQuery.data?.goals.filter((g) =>
      g.account_allocations.some((link) => link.account_id === account.id),
    ) ?? [];

  return (
    <main className="flex flex-1 flex-col gap-3 overflow-y-auto bg-paper p-5">
      <header className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate("/")}
          className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-muted hover:text-ink"
        >
          <ChevronLeft aria-hidden className="h-3 w-3" />
          {t("routes.account.back_to_household")}
        </button>
      </header>

      <section
        className="grid grid-cols-4 gap-3 border border-hairline-2 bg-paper-2 px-5 py-3 shadow-sm"
        aria-label={t("routes.account.kpi_value")}
      >
        <Kpi label={t("routes.account.kpi_value")} value={formatCad(account.current_value)} />
        <Kpi label={t("routes.account.kpi_type")} value={account.type} />
        <Kpi label={t("routes.account.kpi_goal_count")} value={String(goalsInAccount.length)} />
        <Kpi label={t("routes.account.kpi_cash_state")} value={account.cash_state || "—"} />
      </section>

      <section className="grid grid-cols-2 gap-3">
        <div className="border border-hairline-2 bg-paper p-4 shadow-sm">
          <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("routes.account.stats_title")}
          </h3>
          <div className="h-56">
            {ringData.length > 0 ? (
              <RingChart
                data={ringData}
                ariaLabel={t("routes.account.stats_title")}
                centerLabel={t("routes.account.kpi_value")}
                centerValue={formatCadCompact(account.current_value)}
              />
            ) : (
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
                {t("routes.account.no_holdings")}
              </p>
            )}
          </div>
        </div>
        <div className="border border-hairline-2 bg-paper p-4 shadow-sm">
          <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("routes.account.top_funds_title")}
          </h3>
          {barRows.length > 0 ? (
            <AllocationBars
              rows={barRows}
              limit={8}
              ariaLabel={t("routes.account.top_funds_title")}
            />
          ) : (
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("routes.account.no_holdings")}
            </p>
          )}
        </div>
      </section>

      <section className="border border-hairline-2 bg-paper p-4 shadow-sm">
        <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("routes.account.goals_in_account_title")}
        </h3>
        {goalsInAccount.length === 0 ? (
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("routes.account.no_goals_in_account")}
          </p>
        ) : (
          <ul className="flex flex-col divide-y divide-hairline">
            {goalsInAccount.map((goal) => {
              const link = goal.account_allocations.find((l) => l.account_id === account.id);
              const allocated = link ? Number(link.allocated_amount) : 0;
              return (
                <li key={goal.id}>
                  <Link
                    to={`/goal/${encodeURIComponent(goal.id)}`}
                    className="flex items-baseline justify-between py-2 hover:bg-paper-2"
                  >
                    <span className="font-sans text-[12px] font-medium text-ink">{goal.name}</span>
                    <span className="font-mono text-[10px] text-accent-2">
                      {formatCad(allocated)}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</span>
      <span className="font-serif text-lg font-medium text-ink">{value}</span>
    </div>
  );
}

function buildRingData(holdings: Holding[]): RingDatum[] {
  return holdings
    .filter((h) => Number(h.market_value) > 0)
    .map((h, i) => ({
      label: h.sleeve_name,
      value: Number(h.market_value),
      color: colorForFund(h.sleeve_id, i),
    }));
}

function buildBarRows(holdings: Holding[]): AllocationRow[] {
  return holdings
    .filter((h) => h.weight > 0)
    .map((h, i) => ({
      id: h.sleeve_id,
      label: h.sleeve_name,
      pct: Number(h.weight),
      color: colorForFund(h.sleeve_id, i),
    }));
}
