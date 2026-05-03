/**
 * Re-goaling modal — locked decision #15 + canon §6.3a.
 *
 * Vocabulary discipline: this is "re-goaling" / "goal realignment".
 * Holdings never move. The mutation only updates `GoalAccountLink.
 * allocated_amount` rows (label-only). UI strings here have been
 * scanned by `scripts/check-vocab.sh`.
 *
 * UX: per-account section. Each account row sums its goal legs; if
 * the sum doesn't match the account's `current_value`, the row turns
 * danger-colored and the Apply button is disabled until balanced.
 *
 * Open-question #13: the BIG_SHIFT banner trigger is wired through
 * `useBlendedAccountRisk` but the backend threshold is `> 5.0`
 * against canon-1-5 weighted scores (max delta ~4), so the banner
 * will not actually fire today. Frontend is correct; backend fix
 * is one-line and tracked.
 */
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../components/ui/dialog";
import { type Account, type Goal, type HouseholdDetail } from "../lib/household";
import { type RealignmentResponse, useRealignment } from "../lib/realignment";
import { formatCad } from "../lib/format";
import { normalizeApiError } from "../lib/api-error";
import { toastError } from "../lib/toast";
import { cn } from "../lib/cn";

/**
 * Tier-3 polish (§1.9): pre-Apply diff preview.
 *
 * Single CAD formatter for signed deltas. We use the canon
 * `formatCad` for absolute values + manual sign prefix for
 * deltas (keeps "+$1,200" / "-$800" / "—" idiomatic).
 */
const SIGNED_PCT_FORMATTER = new Intl.NumberFormat("en-CA", {
  style: "decimal",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: "always",
});

function formatSignedCad(value: number): string {
  if (Math.abs(value) < 0.5) return "—";
  const sign = value > 0 ? "+" : "-";
  return `${sign}${formatCad(Math.abs(value))}`;
}

function formatSignedPct(value: number): string {
  if (Math.abs(value) < 0.05) return "—";
  return `${SIGNED_PCT_FORMATTER.format(value)}%`;
}

interface RealignModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  household: HouseholdDetail;
  /** Called with the realignment response when Apply succeeds. */
  onApplied: (response: RealignmentResponse) => void;
}

type DraftLegMap = Record<string, Record<string, string>>;

export function RealignModal({ open, onOpenChange, household, onApplied }: RealignModalProps) {
  const { t } = useTranslation();
  const realign = useRealignment(household.id);
  const [draft, setDraft] = useState<DraftLegMap>(() => initialDraft(household));

  // Re-seed the draft if the household ref changes (e.g. parent
  // refetched after a previous realignment landed).
  useEffect(() => {
    if (open) setDraft(initialDraft(household));
  }, [open, household]);

  const accountSums = useMemo(() => computeAccountSums(draft), [draft]);
  const allBalanced = useMemo(
    () =>
      household.accounts.every((acct) => {
        const sum = accountSums[acct.id] ?? 0;
        return Math.abs(sum - Number(acct.current_value)) < 0.005;
      }),
    [accountSums, household.accounts],
  );

  // Tier-3 polish (§1.9): "What's about to change" preview.
  //
  // Recomputes when the draft (or the seed household) changes, so the
  // diff is reactive as the advisor adjusts leg-shift inputs.
  const baseline = useMemo(() => initialDraft(household), [household]);
  const diff = useMemo(
    () => computeDiff(household, baseline, draft),
    [household, baseline, draft],
  );
  const hasChanges = diff.accountDeltas.length > 0 || diff.goalDeltas.length > 0;

  function setLegAmount(accountId: string, goalId: string, value: string) {
    setDraft((prev) => {
      const accountDraft: Record<string, string> = { ...(prev[accountId] ?? {}) };
      accountDraft[goalId] = value;
      return { ...prev, [accountId]: accountDraft };
    });
  }

  function handleApply() {
    realign.mutate(
      { account_goal_amounts: draft },
      {
        onSuccess: (response) => {
          onApplied(response);
          onOpenChange(false);
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("realign.error_generic"));
          toastError(t("realign.error_generic"), { description: e.message });
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-describedby="realign-modal-desc"
        className="!max-h-[85vh] !w-[min(92vw,820px)] p-6"
      >
        <DialogTitle asChild>
          <h2 className="font-serif text-xl font-medium tracking-tight text-ink">
            {t("realign.title")}
          </h2>
        </DialogTitle>
        <DialogDescription id="realign-modal-desc" asChild>
          <p className="mt-1 text-[12px] leading-relaxed text-muted">{t("realign.intro")}</p>
        </DialogDescription>

        <div className="mt-4 flex flex-col gap-4">
          {household.accounts.map((account) => (
            <AccountRow
              key={account.id}
              household={household}
              account={account}
              draft={draft[account.id] ?? {}}
              currentSum={accountSums[account.id] ?? 0}
              onLegChange={(goalId, value) => setLegAmount(account.id, goalId, value)}
            />
          ))}
        </div>

        <PreviewBlock diff={diff} hasChanges={hasChanges} />

        <footer className="mt-5 flex items-center justify-between border-t border-hairline pt-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {allBalanced ? t("realign.legs_balanced") : t("realign.legs_imbalanced")}
          </p>
          <div className="flex gap-2">
            <DialogPrimitive.Close asChild>
              <Button type="button" variant="outline" size="sm">
                {t("common.cancel")}
              </Button>
            </DialogPrimitive.Close>
            <Button
              type="button"
              size="sm"
              onClick={handleApply}
              disabled={!allBalanced || realign.isPending}
            >
              {realign.isPending ? t("realign.applying") : t("realign.apply")}
            </Button>
          </div>
        </footer>
      </DialogContent>
    </Dialog>
  );
}

function AccountRow({
  household,
  account,
  draft,
  currentSum,
  onLegChange,
}: {
  household: HouseholdDetail;
  account: Account;
  draft: Record<string, string>;
  currentSum: number;
  onLegChange: (goalId: string, value: string) => void;
}) {
  const { t } = useTranslation();
  const accountValue = Number(account.current_value);
  const balanced = Math.abs(currentSum - accountValue) < 0.005;
  const linkedGoals = useMemo(
    () => goalsTouchingAccount(household.goals, account.id),
    [household.goals, account.id],
  );

  return (
    <section
      className={cn(
        "border bg-paper p-4 shadow-sm",
        balanced ? "border-hairline-2" : "border-danger",
      )}
      aria-label={t("realign.account_section_label", { type: account.type })}
    >
      <header className="mb-3 flex items-baseline justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {account.type}
        </h3>
        <div className="flex items-baseline gap-3 font-mono text-[11px]">
          <span className="text-muted">{t("realign.account_total")}</span>
          <span className="text-ink">{formatCad(accountValue)}</span>
          <span className={balanced ? "text-success" : "text-danger"}>
            {t("realign.legs_sum", { sum: formatCad(currentSum) })}
          </span>
        </div>
      </header>
      <ul className="flex flex-col gap-1.5">
        {linkedGoals.map((goal) => (
          <li key={goal.id} className="grid grid-cols-[2fr_1fr] items-center gap-3">
            <span className="font-sans text-[12px] text-ink">{goal.name}</span>
            <input
              inputMode="decimal"
              value={draft[goal.id] ?? ""}
              onChange={(e) => onLegChange(goal.id, e.target.value)}
              aria-label={t("realign.leg_input_label", { goal: goal.name })}
              className="border border-hairline-2 bg-paper px-3 py-1.5 text-right font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
            />
          </li>
        ))}
        {linkedGoals.length === 0 && (
          <li className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("realign.no_goals_for_account")}
          </li>
        )}
      </ul>
    </section>
  );
}

function initialDraft(household: HouseholdDetail): DraftLegMap {
  const map: DraftLegMap = {};
  for (const goal of household.goals) {
    for (const link of goal.account_allocations) {
      const accountDraft: Record<string, string> = map[link.account_id] ?? {};
      accountDraft[goal.id] = String(Number(link.allocated_amount).toFixed(2));
      map[link.account_id] = accountDraft;
    }
  }
  return map;
}

function computeAccountSums(draft: DraftLegMap): Record<string, number> {
  const sums: Record<string, number> = {};
  for (const [accountId, legs] of Object.entries(draft)) {
    let total = 0;
    for (const value of Object.values(legs)) {
      const n = Number(value);
      if (Number.isFinite(n)) total += n;
    }
    sums[accountId] = total;
  }
  return sums;
}

function goalsTouchingAccount(goals: Goal[], accountId: string): Goal[] {
  return goals.filter((goal) =>
    goal.account_allocations.some((link) => link.account_id === accountId),
  );
}

// --------------------------------------------------------------------
// Tier-3 polish (§1.9): "What's about to change" preview.
//
// Surfaces the projected deltas implied by the in-flight draft BEFORE
// the user clicks Apply. Per-account totals never move (legs always
// sum to `current_value`); the meaningful diff is per-goal allocation
// shifts and per-account-leg shifts (which legs of which accounts are
// being re-labelled).
//
// Reads from the same `draft` state already used for Apply, so the
// preview re-renders reactively when any leg input changes.
// --------------------------------------------------------------------

type GoalDeltaRow = {
  goalId: string;
  goalName: string;
  beforeAmount: number;
  afterAmount: number;
  deltaAmount: number;
  deltaPct: number;
};

type AccountLegDeltaRow = {
  accountId: string;
  accountType: string;
  goalId: string;
  goalName: string;
  beforeAmount: number;
  afterAmount: number;
  deltaAmount: number;
};

type RealignmentDiff = {
  goalDeltas: GoalDeltaRow[];
  accountDeltas: AccountLegDeltaRow[];
};

function computeDiff(
  household: HouseholdDetail,
  baseline: DraftLegMap,
  draft: DraftLegMap,
): RealignmentDiff {
  const goalNameById: Record<string, string> = {};
  for (const goal of household.goals) goalNameById[goal.id] = goal.name;
  const accountTypeById: Record<string, string> = {};
  for (const acct of household.accounts) accountTypeById[acct.id] = acct.type;

  // Per-goal: sum every account's leg for that goal in baseline vs draft.
  const beforeByGoal: Record<string, number> = {};
  const afterByGoal: Record<string, number> = {};
  const collect = (
    legs: DraftLegMap,
    sink: Record<string, number>,
  ): void => {
    for (const accountLegs of Object.values(legs)) {
      for (const [goalId, value] of Object.entries(accountLegs)) {
        const n = Number(value);
        if (!Number.isFinite(n)) continue;
        sink[goalId] = (sink[goalId] ?? 0) + n;
      }
    }
  };
  collect(baseline, beforeByGoal);
  collect(draft, afterByGoal);

  const goalIds = new Set<string>([
    ...Object.keys(beforeByGoal),
    ...Object.keys(afterByGoal),
  ]);
  const goalDeltas: GoalDeltaRow[] = [];
  for (const goalId of goalIds) {
    const beforeAmount = beforeByGoal[goalId] ?? 0;
    const afterAmount = afterByGoal[goalId] ?? 0;
    const deltaAmount = afterAmount - beforeAmount;
    if (Math.abs(deltaAmount) < 0.5) continue;
    const deltaPct =
      beforeAmount > 0
        ? (deltaAmount / beforeAmount) * 100
        : afterAmount > 0
          ? 100
          : 0;
    goalDeltas.push({
      goalId,
      goalName: goalNameById[goalId] ?? goalId,
      beforeAmount,
      afterAmount,
      deltaAmount,
      deltaPct,
    });
  }
  goalDeltas.sort((a, b) => Math.abs(b.deltaAmount) - Math.abs(a.deltaAmount));

  // Per-account-leg: which (account, goal) cells changed.
  const accountDeltas: AccountLegDeltaRow[] = [];
  const accountIds = new Set<string>([
    ...Object.keys(baseline),
    ...Object.keys(draft),
  ]);
  for (const accountId of accountIds) {
    const beforeLegs = baseline[accountId] ?? {};
    const afterLegs = draft[accountId] ?? {};
    const goalIdsInAcct = new Set<string>([
      ...Object.keys(beforeLegs),
      ...Object.keys(afterLegs),
    ]);
    for (const goalId of goalIdsInAcct) {
      const beforeRaw = Number(beforeLegs[goalId] ?? 0);
      const afterRaw = Number(afterLegs[goalId] ?? 0);
      const beforeAmount = Number.isFinite(beforeRaw) ? beforeRaw : 0;
      const afterAmount = Number.isFinite(afterRaw) ? afterRaw : 0;
      const deltaAmount = afterAmount - beforeAmount;
      if (Math.abs(deltaAmount) < 0.5) continue;
      accountDeltas.push({
        accountId,
        accountType: accountTypeById[accountId] ?? accountId,
        goalId,
        goalName: goalNameById[goalId] ?? goalId,
        beforeAmount,
        afterAmount,
        deltaAmount,
      });
    }
  }
  accountDeltas.sort((a, b) => Math.abs(b.deltaAmount) - Math.abs(a.deltaAmount));

  return { goalDeltas, accountDeltas };
}

function PreviewBlock({
  diff,
  hasChanges,
}: {
  diff: RealignmentDiff;
  hasChanges: boolean;
}) {
  const { t } = useTranslation();
  return (
    <section
      className="mt-5 border border-hairline-2 bg-paper-2 p-4"
      aria-label={t("polish_d.realign_preview.section_label")}
    >
      <header className="mb-2 flex items-baseline justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("polish_d.realign_preview.title")}
        </h3>
        <span className="font-mono text-[10px] text-muted">
          {hasChanges
            ? t("polish_d.realign_preview.has_changes")
            : t("polish_d.realign_preview.no_changes")}
        </span>
      </header>
      {!hasChanges && (
        <p className="font-mono text-[11px] text-muted">
          {t("polish_d.realign_preview.empty_body")}
        </p>
      )}
      {hasChanges && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <PreviewGoalList rows={diff.goalDeltas} />
          <PreviewAccountList rows={diff.accountDeltas} />
        </div>
      )}
    </section>
  );
}

function PreviewGoalList({ rows }: { rows: GoalDeltaRow[] }) {
  const { t } = useTranslation();
  return (
    <div>
      <p className="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-muted">
        {t("polish_d.realign_preview.per_goal_title")}
      </p>
      {rows.length === 0 ? (
        <p className="font-mono text-[11px] text-muted">
          {t("polish_d.realign_preview.no_goal_changes")}
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {rows.map((row) => (
            <li
              key={row.goalId}
              className="grid grid-cols-[2fr_auto_auto] items-baseline gap-2 font-mono text-[11px]"
            >
              <span className="truncate text-ink">{row.goalName}</span>
              <DeltaPill amount={row.deltaAmount} />
              <span className="text-right text-muted">
                {formatSignedPct(row.deltaPct)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PreviewAccountList({ rows }: { rows: AccountLegDeltaRow[] }) {
  const { t } = useTranslation();
  return (
    <div>
      <p className="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-muted">
        {t("polish_d.realign_preview.per_account_title")}
      </p>
      {rows.length === 0 ? (
        <p className="font-mono text-[11px] text-muted">
          {t("polish_d.realign_preview.no_account_changes")}
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {rows.map((row) => (
            <li
              key={`${row.accountId}:${row.goalId}`}
              className="grid grid-cols-[2fr_auto] items-baseline gap-2 font-mono text-[11px]"
            >
              <span className="truncate text-ink">
                {row.accountType}
                <span className="mx-1 text-muted">·</span>
                <span className="text-muted">{row.goalName}</span>
              </span>
              <DeltaPill amount={row.deltaAmount} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DeltaPill({ amount }: { amount: number }) {
  const text = formatSignedCad(amount);
  const positive = amount > 0.5;
  const negative = amount < -0.5;
  return (
    <span
      className={cn(
        "border px-1.5 py-0.5 text-right font-mono text-[10px]",
        positive
          ? "border-success/40 text-success"
          : negative
            ? "border-danger/40 text-danger"
            : "border-hairline text-muted",
      )}
    >
      {text}
    </span>
  );
}
