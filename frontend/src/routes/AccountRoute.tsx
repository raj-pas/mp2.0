import { ChevronLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { ToggleFundAssetClass, useFundAssetMode } from "../chrome/ToggleFundAssetClass";
import { AllocationBars, type AllocationRow } from "../charts/AllocationBars";
import { RingChart, type RingDatum } from "../charts/RingChart";
import { Skeleton } from "../components/ui/skeleton";
import { fundColor } from "../lib/funds";
import { findAccount, type Holding, useHousehold } from "../lib/household";
import { formatCadCompact, formatCurrencyCAD } from "../lib/format";

export function AccountRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { accountId } = useParams<{ accountId: string }>();
  const [rememberedId] = useRememberedClientId();
  const householdQuery = useHousehold(rememberedId);
  const [fundAssetMode] = useFundAssetMode();

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
        <Skeleton className="h-20 w-full" />
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-56 w-full" />
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
          {t("polish_a.account.load_error_title")}
        </p>
        <button
          type="button"
          onClick={() => {
            void householdQuery.refetch();
          }}
          className="border border-hairline-2 bg-paper-2 px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-ink transition-colors hover:bg-paper motion-safe:transition-colors"
        >
          {t("polish_a.account.retry")}
        </button>
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
        <Kpi
          label={t("routes.account.kpi_value")}
          value={formatCurrencyCAD(account.current_value)}
        />
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
          <header className="mb-3 flex items-center justify-between gap-2">
            <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("routes.account.top_funds_title")}
            </h3>
            <ToggleFundAssetClass />
          </header>
          {barRows.length > 0 ? (
            <AllocationBars
              rows={barRows}
              limit={8}
              ariaLabel={t("routes.account.top_funds_title")}
              mode={fundAssetMode}
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
                      {formatCurrencyCAD(allocated)}
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
      color: fundColor(h.sleeve_id, i),
    }));
}

function buildBarRows(holdings: Holding[]): AllocationRow[] {
  return holdings
    .filter((h) => h.weight > 0)
    .map((h, i) => ({
      id: h.sleeve_id,
      label: h.sleeve_name,
      pct: Number(h.weight),
      color: fundColor(h.sleeve_id, i),
    }));
}
