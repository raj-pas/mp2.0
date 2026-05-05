import * as Tabs from "@radix-ui/react-tabs";
import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { useRememberedClientId } from "../chrome/ClientPicker";
import { fundColor } from "../lib/funds";
import { HouseholdHistoryTab } from "./HouseholdHistoryTab";
import {
  type Account,
  type Holding,
  householdExternalAum,
  householdInternalAum,
  useHousehold,
} from "../lib/household";
import { formatCad, formatPct } from "../lib/format";
import { descriptorFor } from "../lib/risk";

interface HouseholdContextProps {
  /**
   * Controlled active-tab value driven by the parent ContextPanel
   * (P3.2 plan v20 §A1.32). Currently used for defensive empty-state
   * rendering; Radix Tabs.Content handles the actual visibility via its
   * parent `Tabs.Root value=` prop.
   */
  tab: string;
}

export function HouseholdContext({ tab: _tab }: HouseholdContextProps) {
  const { t } = useTranslation();
  const [rememberedId] = useRememberedClientId();
  const householdQuery = useHousehold(rememberedId);

  if (householdQuery.isPending) {
    return <Skeleton className="h-32 w-full" />;
  }
  if (householdQuery.data === undefined) {
    return <CtxEmpty body={t("routes.household.missing_client")} />;
  }
  const household = householdQuery.data;
  const internalAum = householdInternalAum(household);
  const totalAum = internalAum + householdExternalAum(household);
  const descriptor = descriptorFor(household.household_risk_score, t);

  return (
    <>
      <Tabs.Content value="overview" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("ctx.section.household")}>
          <p className="font-serif text-base text-ink">{household.display_name}</p>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {household.household_type}
          </p>
        </CtxSection>
        <CtxSection label={t("routes.household.aum_label")}>
          <p className="font-serif text-lg font-medium text-ink">{formatCad(totalAum)}</p>
        </CtxSection>
        <CtxSection label={t("routes.household.risk_score_label")}>
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink">
            {descriptor ?? t("routes.household.risk_score_unset")}
          </p>
        </CtxSection>
        <CtxSection label={t("ctx.section.members")}>
          <ul className="flex flex-col gap-1">
            {household.members.length === 0 && (
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">—</p>
            )}
            {household.members.map((member) => (
              <li key={member.id} className="font-sans text-[12px] text-ink">
                {member.name}
              </li>
            ))}
          </ul>
        </CtxSection>
      </Tabs.Content>

      <Tabs.Content value="allocation" className="flex-1 overflow-y-auto p-3.5">
        <CtxSection label={t("ctx.section.fund_mix")}>
          <FundMixStack
            holdings={collectHouseholdHoldings(household.accounts)}
            total={internalAum}
          />
        </CtxSection>
      </Tabs.Content>

      <Tabs.Content value="projections" className="flex-1 overflow-y-auto p-3.5">
        <CtxEmpty body={t("ctx.deferred.projections_r4")} />
      </Tabs.Content>

      <Tabs.Content value="history" className="flex-1 overflow-y-auto p-3.5">
        <HouseholdHistoryTab />
      </Tabs.Content>
    </>
  );
}

function collectHouseholdHoldings(accounts: Account[]): Holding[] {
  const totals = new Map<
    string,
    { sleeve_id: string; sleeve_name: string; market_value: number }
  >();
  for (const account of accounts) {
    for (const holding of account.holdings) {
      const existing = totals.get(holding.sleeve_id);
      if (existing) {
        existing.market_value += Number(holding.market_value);
      } else {
        totals.set(holding.sleeve_id, {
          sleeve_id: holding.sleeve_id,
          sleeve_name: holding.sleeve_name,
          market_value: Number(holding.market_value),
        });
      }
    }
  }
  return Array.from(totals.values())
    .filter((h) => h.market_value > 0)
    .sort((a, b) => b.market_value - a.market_value)
    .map((h) => ({ ...h, weight: 0 }));
}

function FundMixStack({ holdings, total }: { holdings: Holding[]; total: number }) {
  const { t } = useTranslation();
  if (holdings.length === 0 || total <= 0) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("ctx.deferred.no_holdings")}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-2 w-full overflow-hidden border border-hairline">
        {holdings.slice(0, 12).map((h) => (
          <span
            key={h.sleeve_id}
            style={{
              width: `${(h.market_value / total) * 100}%`,
              background: fundColor(h.sleeve_id),
            }}
            title={`${h.sleeve_name}: ${formatCad(h.market_value)}`}
          />
        ))}
      </div>
      <ul className="flex flex-col gap-1">
        {holdings.slice(0, 8).map((h) => (
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
              {formatPct(h.market_value / total, 1, { multiply100: true })}
            </span>
          </li>
        ))}
      </ul>
    </div>
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

function CtxEmpty({ body }: { body: string }) {
  return <p className="font-mono text-[10px] uppercase tracking-widest text-muted">{body}</p>;
}
