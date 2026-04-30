/**
 * Current vs ideal vs compare bars for a goal's fund mix.
 *
 * Pulls the ideal mix from `/api/preview/sleeve-mix/` (canon score
 * → fund pcts) and current mix by aggregating GoalAccountLink
 * legs across the goal's linked accounts. Locked decision #2 keeps
 * the math server-side; this component does layout + diff only.
 */
import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { fundColor, fundDisplayName, canonizeFundId, type FundCanonId } from "../lib/funds";
import { type Goal, type HouseholdDetail } from "../lib/household";
import { useSleeveMix } from "../lib/preview";
import { formatPct } from "../lib/format";

interface GoalAllocationSectionProps {
  goal: Goal;
  household: HouseholdDetail;
  /** Effective canon score (system or active override). */
  effectiveScore: 1 | 2 | 3 | 4 | 5;
}

export function GoalAllocationSection({
  goal,
  household,
  effectiveScore,
}: GoalAllocationSectionProps) {
  const { t } = useTranslation();
  const sleeveMix = useSleeveMix(effectiveScore);

  const currentMix = useMemo_currentMix(goal, household);

  if (sleeveMix.isPending) {
    return (
      <Section title={t("goal_allocation.section_title")}>
        <Skeleton className="h-32 w-full" />
      </Section>
    );
  }
  if (sleeveMix.isError || sleeveMix.data === undefined) {
    return (
      <Section title={t("goal_allocation.section_title")}>
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("errors.preview_failed")}
        </p>
      </Section>
    );
  }

  const idealMix = normalizeMixToCanon(sleeveMix.data.mix);

  // Union of canon fund ids appearing in either side, ordered by ideal % desc.
  const fundOrder = orderFundsByIdeal(idealMix, currentMix);

  return (
    <Section title={t("goal_allocation.section_title")}>
      <table className="w-full table-fixed">
        <thead>
          <tr className="text-left">
            <th className="w-1/3 pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
              {t("goal_allocation.section_title")}
            </th>
            <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
              {t("goal_allocation.current_label")}
            </th>
            <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
              {t("goal_allocation.ideal_label")}
            </th>
            <th className="pb-2 text-right font-mono text-[9px] uppercase tracking-widest text-muted">
              Δ
            </th>
          </tr>
        </thead>
        <tbody>
          {fundOrder.map((id) => {
            const idealPct = idealMix.get(id) ?? 0;
            const currentPct = currentMix.get(id) ?? 0;
            const delta = idealPct - currentPct;
            return (
              <tr key={id} className="border-t border-hairline">
                <td className="py-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      aria-hidden
                      className="inline-block h-2 w-2"
                      style={{ background: fundColor(id) }}
                    />
                    <span className="truncate font-sans text-[11px] text-ink">
                      {fundDisplayName(id, id)}
                    </span>
                  </div>
                </td>
                <td className="py-1.5">
                  <BarCell pct={currentPct} fundId={id} />
                </td>
                <td className="py-1.5">
                  <BarCell pct={idealPct} fundId={id} />
                </td>
                <td
                  className={
                    delta > 0
                      ? "py-1.5 text-right font-mono text-[10px] text-success"
                      : delta < 0
                        ? "py-1.5 text-right font-mono text-[10px] text-danger"
                        : "py-1.5 text-right font-mono text-[10px] text-muted"
                  }
                >
                  {formatSignedPct(delta)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {fundOrder.length === 0 && (
        <p className="mt-2 font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("goal_allocation.no_holdings")}
        </p>
      )}
    </Section>
  );
}

function BarCell({ pct, fundId }: { pct: number; fundId: FundCanonId | string }) {
  const widthPct = Math.min(100, Math.max(0, pct));
  return (
    <div className="flex items-center gap-2">
      <span className="block h-2 w-full overflow-hidden border border-hairline bg-paper-2">
        <span
          className="block h-full"
          style={{
            width: `${widthPct}%`,
            background: fundColor(fundId),
          }}
        />
      </span>
      <span className="w-10 text-right font-mono text-[10px] text-ink">{formatPct(pct, 1)}</span>
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

function useMemo_currentMix(goal: Goal, household: HouseholdDetail): Map<string, number> {
  // Aggregate fund-level $ across all goal legs, then convert to %.
  const fundDollars = new Map<string, number>();
  let totalDollars = 0;

  for (const link of goal.account_allocations) {
    const allocated = Number(link.allocated_amount || 0);
    if (allocated <= 0) continue;
    const account = household.accounts.find((a) => a.id === link.account_id);
    if (account === undefined) continue;
    const accountValue = Number(account.current_value || 0);
    if (accountValue <= 0) continue;
    const legShare = allocated / accountValue; // fraction of the account this goal claims
    for (const holding of account.holdings) {
      const dollars = Number(holding.market_value || 0) * legShare;
      if (dollars <= 0) continue;
      const canon = canonizeFundId(holding.sleeve_id);
      const key: string = canon ?? holding.sleeve_id;
      fundDollars.set(key, (fundDollars.get(key) ?? 0) + dollars);
      totalDollars += dollars;
    }
  }

  if (totalDollars <= 0) return new Map();
  const result = new Map<string, number>();
  for (const [k, v] of fundDollars) {
    result.set(k, (v / totalDollars) * 100);
  }
  return result;
}

function normalizeMixToCanon(mix: Record<string, number>): Map<string, number> {
  const out = new Map<string, number>();
  for (const [k, v] of Object.entries(mix)) {
    const canon = canonizeFundId(k);
    const key: string = canon ?? k;
    out.set(key, (out.get(key) ?? 0) + Number(v));
  }
  return out;
}

function orderFundsByIdeal(ideal: Map<string, number>, current: Map<string, number>): string[] {
  const ids = new Set<string>([...ideal.keys(), ...current.keys()]);
  return [...ids].sort((a, b) => (ideal.get(b) ?? 0) - (ideal.get(a) ?? 0));
}

function formatSignedPct(pct: number): string {
  if (Math.abs(pct) < 0.05) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}
