/**
 * Current vs ideal vs compare bars for a goal's fund mix.
 *
 * Source-decision tree (locked §3.1 — slider-drag UX):
 *   - `isPreviewingOverride === true` (slider is being dragged for what-if):
 *       → calibration_drag pill; ideal bars track the slider via `useSleeveMix`
 *   - `latest_portfolio_run.output.goal_rollups[goal.id]` exists:
 *       → engine pill with run signature; ideal bars from
 *         `findGoalRollup(household, goal.id).allocations` (engine's
 *         dollar-weighted, frontier-optimized blend per locked §3.5)
 *   - Otherwise (no engine rollup, no drag):
 *       → calibration pill; ideal bars from `useSleeveMix(effectiveScore)`
 *
 * Per locked decision §3.7: `isPreviewingOverride` is lifted from
 * `RiskSlider.isOverrideDraft` to `GoalRoute` and passed down here.
 */
import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { fundColor, fundDisplayName, canonizeFundId, type FundCanonId } from "../lib/funds";
import {
  type Allocation,
  type Goal,
  type HouseholdDetail,
  findGoalRollup,
} from "../lib/household";
import { useSleeveMix } from "../lib/preview";
import { formatPct } from "../lib/format";
import { SourcePill, type PillSource } from "./SourcePill";

interface GoalAllocationSectionProps {
  goal: Goal;
  household: HouseholdDetail;
  /** Effective canon score (system or active override). */
  effectiveScore: 1 | 2 | 3 | 4 | 5;
  /**
   * True when the advisor is dragging the risk slider but hasn't yet
   * saved the override. Per locked §3.1: in this state, ideal bars
   * track the slider via calibration (live what-if), not the engine
   * (which is fixed to the saved goal config).
   */
  isPreviewingOverride?: boolean;
}

export function GoalAllocationSection({
  goal,
  household,
  effectiveScore,
  isPreviewingOverride = false,
}: GoalAllocationSectionProps) {
  const { t } = useTranslation();

  // Always call useSleeveMix so the calibration query is ready when we
  // need it (no conditional hooks; React rules of hooks).
  const sleeveMix = useSleeveMix(effectiveScore);

  const goalRollup = findGoalRollup(household, goal.id);
  const useEnginePath = goalRollup !== null && !isPreviewingOverride;
  const source: PillSource = isPreviewingOverride
    ? "calibration_drag"
    : goalRollup !== null
      ? "engine"
      : "calibration";
  const runSignature = household.latest_portfolio_run?.run_signature ?? null;

  const currentMix = useMemo_currentMix(goal, household);

  // Engine path: derive ideal mix from goal_rollup.allocations (no calibration query needed).
  if (useEnginePath && goalRollup !== null) {
    const idealMix = buildMixFromAllocations(goalRollup.allocations);
    const fundOrder = orderFundsByIdeal(idealMix, currentMix);
    return (
      <Section title={t("goal_allocation.section_title")} pill={
        <SourcePill source={source} runSignature={runSignature} />
      }>
        <AllocationTable
          fundOrder={fundOrder}
          currentMix={currentMix}
          idealMix={idealMix}
          t={t}
        />
      </Section>
    );
  }

  // Calibration path (fallback or drag preview): use useSleeveMix.
  if (sleeveMix.isPending) {
    return (
      <Section title={t("goal_allocation.section_title")} pill={
        <SourcePill source={source} runSignature={runSignature} />
      }>
        <Skeleton className="h-32 w-full" />
      </Section>
    );
  }
  if (sleeveMix.isError || sleeveMix.data === undefined) {
    return (
      <Section title={t("goal_allocation.section_title")} pill={
        <SourcePill source={source} runSignature={runSignature} />
      }>
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
    <Section title={t("goal_allocation.section_title")} pill={
      <SourcePill source={source} runSignature={runSignature} />
    }>
      <AllocationTable
        fundOrder={fundOrder}
        currentMix={currentMix}
        idealMix={idealMix}
        t={t}
      />
    </Section>
  );
}

interface AllocationTableProps {
  fundOrder: string[];
  currentMix: Map<string, number>;
  idealMix: Map<string, number>;
  t: (key: string) => string;
}

function AllocationTable({ fundOrder, currentMix, idealMix, t }: AllocationTableProps) {
  return (
    <>
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
    </>
  );
}

function buildMixFromAllocations(allocations: Allocation[]): Map<string, number> {
  const out = new Map<string, number>();
  for (const a of allocations) {
    const canon = canonizeFundId(a.sleeve_id) ?? a.sleeve_id;
    // Allocation.weight is 0..1 (per engine schema); BarCell consumes 0..100.
    out.set(canon, (out.get(canon) ?? 0) + a.weight * 100);
  }
  return out;
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
