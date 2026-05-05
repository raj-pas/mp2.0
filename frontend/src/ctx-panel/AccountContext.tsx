import * as Tabs from "@radix-ui/react-tabs";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { useRememberedClientId } from "../chrome/ClientPicker";
import { Skeleton } from "../components/ui/skeleton";
import { fundColor } from "../lib/funds";
import { findAccount, useHousehold } from "../lib/household";
import { formatCad, formatPct } from "../lib/format";

interface AccountContextProps {
  /**
   * Controlled active-tab value driven by the parent ContextPanel
   * (P3.2 plan v20 §A1.32). Radix Tabs.Content handles visibility via
   * the parent Tabs.Root; the prop is plumbed for explicit contract +
   * future per-tab data fetching.
   */
  tab: string;
}

export function AccountContext({ tab: _tab }: AccountContextProps) {
  const { t } = useTranslation();
  const { accountId } = useParams<{ accountId: string }>();
  const [rememberedId] = useRememberedClientId();
  const householdQuery = useHousehold(rememberedId);

  if (householdQuery.isPending) {
    return <Skeleton className="h-32 w-full" />;
  }
  const account =
    accountId !== undefined && householdQuery.data
      ? findAccount(householdQuery.data, accountId)
      : null;
  if (account === null) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-danger">
        {t("routes.account.missing_account")}
      </p>
    );
  }

  const sortedHoldings = account.holdings
    .slice()
    .filter((h) => h.weight > 0)
    .sort((a, b) => b.weight - a.weight);
  const goalsInAccount =
    householdQuery.data?.goals.filter((g) =>
      g.account_allocations.some((link) => link.account_id === account.id),
    ) ?? [];

  return (
    <>
      <Tabs.Content value="overview" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("ctx.section.account")}>
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink">{account.type}</p>
        </CtxSection>
        <CtxSection label={t("routes.account.kpi_value")}>
          <p className="font-serif text-lg font-medium text-ink">
            {formatCad(account.current_value)}
          </p>
        </CtxSection>
        {account.regulatory_objective !== null && (
          <CtxSection label={t("ctx.section.reg_objective")}>
            <p className="font-sans text-[12px] text-ink">{account.regulatory_objective}</p>
          </CtxSection>
        )}
        {account.regulatory_time_horizon !== null && (
          <CtxSection label={t("ctx.section.reg_horizon")}>
            <p className="font-sans text-[12px] text-ink">{account.regulatory_time_horizon}</p>
          </CtxSection>
        )}
      </Tabs.Content>

      <Tabs.Content value="allocation" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("routes.account.top_funds_title")}>
          {sortedHoldings.length === 0 ? (
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("routes.account.no_holdings")}
            </p>
          ) : (
            <ul className="flex flex-col gap-1">
              {sortedHoldings.slice(0, 8).map((h) => (
                <li
                  key={h.sleeve_id}
                  className="flex items-baseline justify-between font-mono text-[10px]"
                >
                  <span className="flex items-center gap-1.5">
                    <span
                      aria-hidden
                      className="inline-block h-2 w-2"
                      style={{ background: fundColor(h.sleeve_id) }}
                    />
                    <span className="text-ink">{h.sleeve_name}</span>
                  </span>
                  <span className="text-accent-2">
                    {formatPct(h.weight, 1, { multiply100: true })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CtxSection>
      </Tabs.Content>

      <Tabs.Content value="goals" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("routes.account.goals_in_account_title")}>
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
                  <li
                    key={goal.id}
                    className="flex items-baseline justify-between py-1.5 font-mono text-[10px]"
                  >
                    <span className="text-ink">{goal.name}</span>
                    <span className="text-accent-2">{formatCad(allocated)}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </CtxSection>
      </Tabs.Content>
    </>
  );
}

function CtxSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="mb-4 last:mb-0">
      <p className="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-muted">{label}</p>
      {children}
    </section>
  );
}
