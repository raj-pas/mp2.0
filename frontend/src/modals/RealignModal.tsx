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
