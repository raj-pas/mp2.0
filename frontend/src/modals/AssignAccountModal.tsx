/**
 * AssignAccountModal — plan v20 §A1.28 (P13 / G13).
 *
 * Lets the advisor assign an account's full balance across one or more
 * goals (existing OR new-inline). Sum-validator hard-requires 100%
 * allocation per §A1.14 #6. $+% inputs link via live conversion per
 * §A1.14 #12. New-goal inline form carries full fields per §A1.14 #17.
 *
 * Code-split via React.lazy from HouseholdRoute / UnallocatedBanner CTA /
 * Treemap unallocated tile click per §A1.20 bundle budget.
 *
 * Vocabulary discipline (canon §6.3a + locked decision #14):
 *   ✅ "Assign", "goal-account-link"
 *   ❌ "transfer", "reallocation", "move money"
 *
 * Wire shape mirrors `AssignAccountToGoalsView` (web/api/views.py P13):
 *   {
 *     rationale: str,            # ≥4 chars; never persisted to audit text
 *     assignments: [
 *       { goal_id: "<existing>", allocated_amount_basis_points: int },
 *       { goal_id: "new", new_goal: { ... }, allocated_amount_basis_points: int },
 *       ...
 *     ]
 *   }
 *
 * Default-export the component so Suspense + React.lazy can import it.
 */
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../components/ui/dialog";
import {
  type AssignAccountAssignment,
  useAssignAccountToGoals,
} from "../lib/household";
import { type Account, type Goal, type HouseholdDetail } from "../lib/household";
import { normalizeApiError } from "../lib/api-error";
import { formatCad } from "../lib/format";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";

export interface AssignAccountModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  household: HouseholdDetail;
  /** Pre-focused account id on open. The modal renders nothing meaningful
   * until this is non-null + matches a household account. */
  accountId: string | null;
  /** Optional callback when assign succeeds (receives the refreshed
   *  HouseholdDetail). Parent wires this to refetch + toast. */
  onAssigned?: (next: HouseholdDetail) => void;
}

type ExistingRowDraft = {
  /** Stable React key so input identity survives re-renders. */
  rowKey: string;
  goal_id: string; // external_id of the goal
  amount_input: string; // free-text $ value as typed
};

type NewGoalRowDraft = {
  rowKey: string;
  goal_id: "new";
  amount_input: string;
  name: string;
  target_amount_input: string;
  necessity_score: number;
  risk_score: number;
  target_date: string;
};

type RowDraft = ExistingRowDraft | NewGoalRowDraft;

function isNewGoalRow(row: RowDraft): row is NewGoalRowDraft {
  return row.goal_id === "new";
}

function parseAmount(input: string): number {
  // Accept "$12,345.67" / "12345.67" / "12345" — strip non-numeric chars
  // except the decimal point. Returns NaN on empty / invalid input.
  if (!input) return NaN;
  const cleaned = input.replace(/[^0-9.]/g, "");
  if (!cleaned) return NaN;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : NaN;
}

function dollarsToBasisPoints(n: number): number {
  // 1 bp = 0.0001 dollars; basis-points-per-dollar = 10_000.
  return Math.round(n * 10_000);
}

/**
 * Default-export so callers can React.lazy(() => import("./AssignAccountModal")).
 */
export default function AssignAccountModal({
  open,
  onOpenChange,
  household,
  accountId,
  onAssigned,
}: AssignAccountModalProps) {
  const { t } = useTranslation();
  const account: Account | undefined = useMemo(
    () => household.accounts.find((a) => a.id === accountId),
    [household.accounts, accountId],
  );
  const accountValue = account ? Number(account.current_value) : 0;
  const accountValueBp = dollarsToBasisPoints(accountValue);

  // Seed rows from existing GoalAccountLinks targeting this account; if
  // none exist (cold-start), initialize empty.
  const [rows, setRows] = useState<RowDraft[]>([]);
  const [rationale, setRationale] = useState("");
  const assignMutation = useAssignAccountToGoals(household.id, accountId ?? null);

  useEffect(() => {
    if (!open || account === undefined) return;
    const existingRows: RowDraft[] = household.goals
      .map((g) => {
        const link = g.account_allocations.find((l) => l.account_id === account.id);
        if (link === undefined) return null;
        const row: ExistingRowDraft = {
          rowKey: `goal:${g.id}`,
          goal_id: g.id,
          amount_input: String(Number(link.allocated_amount).toFixed(2)),
        };
        return row;
      })
      .filter((r): r is ExistingRowDraft => r !== null);
    setRows(existingRows);
    setRationale("");
  }, [open, account, household.goals]);

  if (!open || account === undefined || accountId === null) {
    // Render the Dialog with `open=false` so the unmount cleanly
    // tears down portal nodes — leaves the modal addressable to
    // tests via state.
    return (
      <Dialog open={false} onOpenChange={onOpenChange}>
        <></>
      </Dialog>
    );
  }

  const totalAssignedDollars = rows.reduce((sum, row) => {
    const n = parseAmount(row.amount_input);
    return sum + (Number.isFinite(n) ? n : 0);
  }, 0);
  const totalAssignedBp = dollarsToBasisPoints(totalAssignedDollars);
  // §A1.14 #6 — hard-require 100% (within 1bp tolerance per backend).
  const balancedWithinTolerance = Math.abs(totalAssignedBp - accountValueBp) <= 1;
  const totalPct = accountValue > 0 ? (totalAssignedDollars / accountValue) * 100 : 0;

  const trimmedRationale = rationale.trim();
  const rationaleValid = trimmedRationale.length >= 4;

  const noEmptyRows = rows.every((row) => {
    const n = parseAmount(row.amount_input);
    return Number.isFinite(n) && n > 0;
  });

  // New-goal payload validity: every "new" row needs full fields per §A1.14 #17.
  const newGoalRowsValid = rows.every((row) => {
    if (!isNewGoalRow(row)) return true;
    if (row.name.trim().length === 0) return false;
    const target = parseAmount(row.target_amount_input);
    if (!Number.isFinite(target) || target <= 0) return false;
    if (row.necessity_score < 1 || row.necessity_score > 5) return false;
    if (row.risk_score < 1 || row.risk_score > 5) return false;
    if (!row.target_date) return false;
    return true;
  });

  const goalIdsInUse = new Set(rows.filter((r) => !isNewGoalRow(r)).map((r) => r.goal_id));
  const noDuplicates =
    rows.filter((r) => !isNewGoalRow(r)).length === goalIdsInUse.size;

  const submittable =
    rationaleValid &&
    rows.length > 0 &&
    balancedWithinTolerance &&
    noEmptyRows &&
    newGoalRowsValid &&
    noDuplicates &&
    !assignMutation.isPending;

  const availableGoals: Goal[] = household.goals.filter(
    (g) => !goalIdsInUse.has(g.id) || rows.some((r) => !isNewGoalRow(r) && r.goal_id === g.id),
  );

  function setRowAmount(rowKey: string, value: string) {
    setRows((prev) =>
      prev.map((row) => (row.rowKey === rowKey ? { ...row, amount_input: value } : row)),
    );
  }

  function setRowFromPctInput(rowKey: string, pctInput: string) {
    // §A1.14 #12 live conversion — % typed → $ recomputed against
    // account_value. Empty input → empty $ (don't auto-coerce to 0).
    const pct = parseAmount(pctInput);
    if (!Number.isFinite(pct)) {
      setRowAmount(rowKey, "");
      return;
    }
    const dollars = (pct / 100) * accountValue;
    setRowAmount(rowKey, dollars > 0 ? dollars.toFixed(2) : "");
  }

  function setRowGoalId(rowKey: string, goalId: string) {
    setRows((prev) => prev.map((row) => {
      if (row.rowKey !== rowKey) return row;
      if (goalId === "new") {
        const draft: NewGoalRowDraft = {
          rowKey: row.rowKey,
          goal_id: "new",
          amount_input: row.amount_input,
          name: "",
          target_amount_input: "",
          necessity_score: 3,
          risk_score: 3,
          target_date: "",
        };
        return draft;
      }
      const draft: ExistingRowDraft = {
        rowKey: row.rowKey,
        goal_id: goalId,
        amount_input: row.amount_input,
      };
      return draft;
    }));
  }

  function setNewGoalField(rowKey: string, field: keyof NewGoalRowDraft, value: string | number) {
    setRows((prev) =>
      prev.map((row) => {
        if (row.rowKey !== rowKey || !isNewGoalRow(row)) return row;
        return { ...row, [field]: value } as NewGoalRowDraft;
      }),
    );
  }

  function addExistingRow() {
    const remaining = household.goals.find((g) => !goalIdsInUse.has(g.id));
    if (remaining === undefined) {
      addNewGoalRow();
      return;
    }
    setRows((prev) => [
      ...prev,
      {
        rowKey: `goal:${remaining.id}:${Date.now()}`,
        goal_id: remaining.id,
        amount_input: "",
      },
    ]);
  }

  function addNewGoalRow() {
    const draft: NewGoalRowDraft = {
      rowKey: `new:${Date.now()}:${Math.random().toString(36).slice(2)}`,
      goal_id: "new",
      amount_input: "",
      name: "",
      target_amount_input: "",
      necessity_score: 3,
      risk_score: 3,
      target_date: "",
    };
    setRows((prev) => [...prev, draft]);
  }

  function removeRow(rowKey: string) {
    setRows((prev) => prev.filter((row) => row.rowKey !== rowKey));
  }

  function handleSubmit() {
    if (!submittable || account === undefined) return;
    const assignments: AssignAccountAssignment[] = rows.map((row) => {
      const dollars = parseAmount(row.amount_input);
      const bp = dollarsToBasisPoints(dollars);
      if (isNewGoalRow(row)) {
        return {
          goal_id: "new",
          new_goal: {
            name: row.name.trim(),
            target_amount_basis_points: dollarsToBasisPoints(parseAmount(row.target_amount_input)),
            necessity_score: row.necessity_score,
            risk_score: row.risk_score,
            target_date: row.target_date,
          },
          allocated_amount_basis_points: bp,
        };
      }
      return {
        goal_id: row.goal_id,
        allocated_amount_basis_points: bp,
      };
    });
    assignMutation.mutate(
      { rationale: trimmedRationale, assignments },
      {
        onSuccess: (next) => {
          toastSuccess(
            t("assign_account.toast_success_title"),
            t("assign_account.toast_success_body"),
          );
          onAssigned?.(next);
          onOpenChange(false);
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("assign_account.error_generic"));
          toastError(t("assign_account.error_title"), { description: e.message });
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-describedby="assign-modal-desc"
        className="!max-h-[88vh] !w-[min(92vw,720px)] p-6"
      >
        <DialogTitle asChild>
          <h2 className="font-serif text-xl font-medium tracking-tight text-ink">
            {t("assign_account.title")}
          </h2>
        </DialogTitle>
        <DialogDescription id="assign-modal-desc" asChild>
          <p className="mt-1 text-[12px] leading-relaxed text-muted">
            {t("assign_account.intro", {
              account: account.type,
              amount: formatCad(accountValue),
            })}
          </p>
        </DialogDescription>

        <section className="mt-4 flex flex-col gap-3" data-testid="assign-rows">
          {rows.map((row) => (
            <AssignmentRow
              key={row.rowKey}
              row={row}
              account={account}
              accountValue={accountValue}
              availableGoals={availableGoals}
              onAmountChange={(v) => setRowAmount(row.rowKey, v)}
              onPctChange={(v) => setRowFromPctInput(row.rowKey, v)}
              onGoalIdChange={(v) => setRowGoalId(row.rowKey, v)}
              onNewGoalFieldChange={(f, v) => setNewGoalField(row.rowKey, f, v)}
              onRemove={() => removeRow(row.rowKey)}
            />
          ))}
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addExistingRow}
              data-testid="add-existing-goal"
            >
              <Plus aria-hidden className="mr-1 h-3 w-3" />
              {t("assign_account.add_existing_row")}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addNewGoalRow}
              data-testid="add-new-goal"
            >
              <Plus aria-hidden className="mr-1 h-3 w-3" />
              {t("assign_account.add_new_goal_row")}
            </Button>
          </div>
        </section>

        <section className="mt-4 border-t border-hairline pt-3" aria-live="polite">
          <p
            data-testid="assign-sum-validator"
            className={cn(
              "font-mono text-[11px] uppercase tracking-widest",
              balancedWithinTolerance ? "text-success" : "text-warning",
            )}
          >
            {t("assign_account.sum_label", {
              assigned: formatCad(totalAssignedDollars),
              total: formatCad(accountValue),
              pct: totalPct.toFixed(1),
            })}
          </p>
        </section>

        <section className="mt-3 flex flex-col gap-1.5">
          <label
            htmlFor="assign-rationale"
            className="font-mono text-[10px] uppercase tracking-widest text-muted"
          >
            {t("assign_account.rationale_label")}
          </label>
          <textarea
            id="assign-rationale"
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            rows={2}
            aria-describedby="assign-rationale-hint"
            className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
            placeholder={t("assign_account.rationale_placeholder")}
          />
          <p id="assign-rationale-hint" className="font-mono text-[10px] text-muted">
            {rationaleValid
              ? t("assign_account.rationale_ok")
              : t("assign_account.rationale_min", { min: 4 })}
          </p>
        </section>

        <footer className="mt-5 flex items-center justify-between border-t border-hairline pt-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {balancedWithinTolerance
              ? t("assign_account.ready_balanced")
              : t("assign_account.ready_not_balanced")}
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
              onClick={handleSubmit}
              disabled={!submittable}
              data-testid="assign-submit"
            >
              {assignMutation.isPending
                ? t("assign_account.applying")
                : t("assign_account.apply")}
            </Button>
          </div>
        </footer>
      </DialogContent>
    </Dialog>
  );
}

function AssignmentRow({
  row,
  account,
  accountValue,
  availableGoals,
  onAmountChange,
  onPctChange,
  onGoalIdChange,
  onNewGoalFieldChange,
  onRemove,
}: {
  row: RowDraft;
  account: Account;
  accountValue: number;
  availableGoals: Goal[];
  onAmountChange: (v: string) => void;
  onPctChange: (v: string) => void;
  onGoalIdChange: (v: string) => void;
  onNewGoalFieldChange: (
    field: keyof NewGoalRowDraft,
    value: string | number,
  ) => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  const dollars = parseAmount(row.amount_input);
  const pctValue =
    accountValue > 0 && Number.isFinite(dollars)
      ? ((dollars / accountValue) * 100).toFixed(2)
      : "";

  return (
    <div
      data-testid="assign-row"
      className="border border-hairline-2 bg-paper p-3"
    >
      <div className="grid grid-cols-[2fr_1fr_1fr_auto] items-center gap-3">
        <select
          aria-label={t("assign_account.row_goal_label", { account: account.type })}
          value={row.goal_id}
          onChange={(e) => onGoalIdChange(e.target.value)}
          className="border border-hairline bg-paper px-2 py-1.5 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
        >
          {availableGoals.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
          <option value="new">{t("assign_account.option_new_goal")}</option>
        </select>
        <input
          inputMode="decimal"
          value={row.amount_input}
          onChange={(e) => onAmountChange(e.target.value)}
          aria-label={t("assign_account.row_dollars_label")}
          placeholder="$"
          className="border border-hairline-2 bg-paper px-2 py-1.5 text-right font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
        />
        <input
          inputMode="decimal"
          value={pctValue}
          onChange={(e) => onPctChange(e.target.value)}
          aria-label={t("assign_account.row_pct_label")}
          placeholder="%"
          className="border border-hairline-2 bg-paper px-2 py-1.5 text-right font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
        />
        <button
          type="button"
          onClick={onRemove}
          aria-label={t("assign_account.remove_row")}
          className="grid h-7 w-7 place-items-center text-muted hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <Trash2 aria-hidden className="h-4 w-4" />
        </button>
      </div>
      {isNewGoalRow(row) && (
        <NewGoalFields
          row={row}
          onChange={onNewGoalFieldChange}
        />
      )}
    </div>
  );
}

function NewGoalFields({
  row,
  onChange,
}: {
  row: NewGoalRowDraft;
  onChange: (field: keyof NewGoalRowDraft, value: string | number) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="mt-3 grid grid-cols-1 gap-2 border-t border-hairline pt-3 md:grid-cols-2">
      <div className="flex flex-col gap-1">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("assign_account.new_goal.name_label")}
        </label>
        <input
          value={row.name}
          onChange={(e) => onChange("name", e.target.value)}
          aria-label={t("assign_account.new_goal.name_label")}
          className="border border-hairline-2 bg-paper px-2 py-1.5 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("assign_account.new_goal.target_label")}
        </label>
        <input
          inputMode="decimal"
          value={row.target_amount_input}
          onChange={(e) => onChange("target_amount_input", e.target.value)}
          aria-label={t("assign_account.new_goal.target_label")}
          placeholder="$"
          className="border border-hairline-2 bg-paper px-2 py-1.5 text-right font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("assign_account.new_goal.target_date_label")}
        </label>
        <input
          type="date"
          value={row.target_date}
          onChange={(e) => onChange("target_date", e.target.value)}
          aria-label={t("assign_account.new_goal.target_date_label")}
          className="border border-hairline-2 bg-paper px-2 py-1.5 font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col gap-1">
          <label className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("assign_account.new_goal.necessity_label")}
          </label>
          <select
            value={row.necessity_score}
            onChange={(e) => onChange("necessity_score", Number(e.target.value))}
            aria-label={t("assign_account.new_goal.necessity_label")}
            className="border border-hairline bg-paper px-2 py-1.5 font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("assign_account.new_goal.risk_label")}
          </label>
          <select
            value={row.risk_score}
            onChange={(e) => onChange("risk_score", Number(e.target.value))}
            aria-label={t("assign_account.new_goal.risk_label")}
            className="border border-hairline bg-paper px-2 py-1.5 font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
