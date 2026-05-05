/**
 * Wizard step 3 — accounts (mini) + goals with per-account leg allocator.
 *
 * Server enforces that each goal's leg amounts sum to the goal value
 * if `target_amount` is set; for goals without a target, sum is the
 * source of truth. Server also validates that `account_index` points
 * to a real account (we wire this client-side via the schema's
 * superRefine).
 *
 * Necessity score → tier mapping (locked decision #6 + #10):
 *   5/4 → Need; 3 → Want; 2/1 → Wish; null → Unsure.
 */
import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, useFormContext, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { formatCadCompact, formatPct } from "../lib/format";
import { ACCOUNT_TYPES, type WizardDraft } from "./schema";

/**
 * Allocation-matrix display caps (§A1.50 P14 row): cap 8x8; "+N more"
 * overflow indicators on rows + cols beyond. Avoids unbounded growth
 * for advisors with many goals/accounts.
 */
const MATRIX_DISPLAY_CAP = 8;

/**
 * Parse a structured zod issue message produced by `schema.ts`
 * superRefine. The schema encodes i18n key + params as a JSON string
 * so the surface can render localized + parameterized copy.
 */
function parseStructuredIssue(
  message: string | undefined,
): { key: string; params: Record<string, unknown> } | null {
  if (message === undefined) return null;
  if (!message.startsWith("{")) return null;
  try {
    const parsed = JSON.parse(message);
    if (typeof parsed === "object" && parsed !== null && "key" in parsed) {
      return {
        key: String(parsed.key),
        params: (parsed.params ?? {}) as Record<string, unknown>,
      };
    }
  } catch {
    // Fall through; treat as plain text below.
  }
  return null;
}

export function Step3Goals() {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const { register, control, formState } = form;
  const accounts = useFieldArray({ control, name: "accounts" });
  const goals = useFieldArray({ control, name: "goals" });
  const accountValues = useWatch({ control, name: "accounts" });
  const goalValues = useWatch({ control, name: "goals" });

  // Per-account allocation summary (P14 §A1.14 #5 LOCKED): assigned
  // dollars + percentage. Matches the backend account-centric gate at
  // web/api/review_state.py:380-385.
  const accountSummaries = (accountValues ?? []).map((acct, accIdx) => {
    const acctValue = Number(acct?.current_value ?? "0");
    let allocated = 0;
    for (const goal of goalValues ?? []) {
      for (const leg of goal?.legs ?? []) {
        if (leg?.account_index === accIdx) {
          const legAmount = Number(leg?.allocated_amount ?? "0");
          if (Number.isFinite(legAmount)) allocated += legAmount;
        }
      }
    }
    const fullyAllocated =
      Number.isFinite(acctValue) && Math.abs(allocated - acctValue) <= 0.01;
    const pct =
      Number.isFinite(acctValue) && acctValue > 0 ? (allocated / acctValue) * 100 : 0;
    return { accIdx, acctValue, allocated, pct, fullyAllocated };
  });

  return (
    <section
      aria-labelledby="wizard-step3-title"
      className="flex flex-col gap-5 border border-hairline-2 bg-paper p-6 shadow-sm"
    >
      <header>
        <h2
          id="wizard-step3-title"
          className="font-serif text-xl font-medium tracking-tight text-ink"
        >
          {t("wizard.step3.title")}
        </h2>
        <p className="mt-1 text-[12px] text-muted">{t("wizard.step3.subtitle")}</p>
      </header>

      {/* Accounts mini-section */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("wizard.step3.accounts_title")}
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              accounts.append({
                account_type: "Non-Registered",
                current_value: "",
                custodian: "",
                missing_holdings_confirmed: false,
              })
            }
            aria-label={t("wizard.step3.add_account")}
          >
            <Plus aria-hidden className="h-3 w-3" />
            <span>{t("wizard.step3.add_account")}</span>
          </Button>
        </div>
        <div className="flex flex-col gap-3">
          {accounts.fields.map((field, index) => {
            const summary = accountSummaries[index];
            const accountIssue = parseStructuredIssue(
              formState.errors.accounts?.[index]?.current_value?.message,
            );
            const showAllocationIndicator =
              summary !== undefined && summary.acctValue > 0;
            return (
              <div
                key={field.id}
                className="flex flex-col gap-1.5 border border-hairline bg-paper-2 p-2"
              >
                <div className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2">
                  <select
                    {...register(`accounts.${index}.account_type` as const)}
                    className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
                  >
                    {ACCOUNT_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                  <input
                    {...register(`accounts.${index}.current_value` as const)}
                    placeholder={t("wizard.step3.value_placeholder")}
                    inputMode="decimal"
                    className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
                  />
                  <input
                    {...register(`accounts.${index}.custodian` as const)}
                    placeholder={t("wizard.step3.custodian_placeholder")}
                    className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => accounts.remove(index)}
                    aria-label={t("wizard.step3.remove_account")}
                    disabled={accounts.fields.length <= 1}
                  >
                    <Trash2 aria-hidden className="h-3.5 w-3.5" />
                  </Button>
                </div>
                {/* Per canon §9.4.5 + locked decision (this session): explicit
                    advisor opt-in for "no fund-level holdings to track". When
                    unchecked + no holdings entered, the engine-readiness check
                    fires post-commit (advisor sees the blocker on the household
                    route + commit response includes the warning). */}
                <label className="flex items-center gap-2 px-1 font-sans text-[11px] text-muted">
                  <input
                    type="checkbox"
                    {...register(`accounts.${index}.missing_holdings_confirmed` as const)}
                    className="h-3 w-3 border-hairline-2 accent-accent"
                  />
                  <span>{t("wizard.step3.missing_holdings_confirmed_label")}</span>
                </label>
                {/* Per-account allocation indicator (P14 §A1.14 #5 LOCKED).
                    Visual feedback uses --warning when not 100%; --danger
                    only when the schema's account-centric gate has flagged
                    the row (accountIssue !== null). Mirrors the post-commit
                    BlockerBanner copy. */}
                {showAllocationIndicator && summary !== undefined && (
                  <p
                    role="status"
                    data-testid={`account-allocation-indicator-${index}`}
                    className={`px-1 font-mono text-[11px] ${
                      accountIssue !== null
                        ? "text-danger"
                        : summary.fullyAllocated
                          ? "text-muted"
                          : "text-warning"
                    }`}
                  >
                    {t("wizard.step3.account_allocation_indicator", {
                      allocated: formatCadCompact(summary.allocated),
                      account_value: formatCadCompact(summary.acctValue),
                      pct: formatPct(summary.pct, 0),
                    })}
                  </p>
                )}
                {accountIssue !== null && (
                  <p
                    role="alert"
                    className="px-1 font-mono text-[10px] text-danger"
                  >
                    {t(accountIssue.key, {
                      ...accountIssue.params,
                      account_value: formatCadCompact(
                        Number(accountIssue.params.account_value ?? 0),
                      ),
                      allocated: formatCadCompact(
                        Number(accountIssue.params.allocated ?? 0),
                      ),
                      unallocated: formatCadCompact(
                        Number(accountIssue.params.unallocated ?? 0),
                      ),
                    })}
                  </p>
                )}
              </div>
            );
          })}
        </div>
        {formState.errors.accounts?.message !== undefined && (
          <p role="alert" className="font-mono text-[10px] text-danger">
            {formState.errors.accounts.message}
          </p>
        )}
      </div>

      {/* Goals section */}
      <div className="flex flex-col gap-3 border-t border-hairline pt-5">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("wizard.step3.goals_title")}
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              goals.append({
                name: "",
                target_date: "",
                necessity_score: 3,
                target_amount: "",
                legs: [{ account_index: 0, allocated_amount: "" }],
              })
            }
            aria-label={t("wizard.step3.add_goal")}
          >
            <Plus aria-hidden className="h-3 w-3" />
            <span>{t("wizard.step3.add_goal")}</span>
          </Button>
        </div>

        {goals.fields.map((field, gIdx) => (
          <GoalRow
            key={field.id}
            index={gIdx}
            onRemove={() => goals.remove(gIdx)}
            removable={goals.fields.length > 1}
            accountTypes={accountValues?.map((a) => a.account_type) ?? []}
          />
        ))}
        {formState.errors.goals?.message !== undefined && (
          <p role="alert" className="font-mono text-[10px] text-danger">
            {formState.errors.goals.message}
          </p>
        )}
      </div>

      <AllocationMatrixPreview
        accounts={accountValues ?? []}
        goals={goalValues ?? []}
      />
    </section>
  );
}

/**
 * Allocation matrix preview (P14 §A1.14 #5 + §A1.50 P14 row).
 *
 * Rows = goals; cols = accounts; cells = allocated dollars (compact CAD)
 * or "—" when no leg exists for that pair. Cap 8x8 to keep the preview
 * scannable; "+N more" overflow indicators at right edge / bottom edge
 * when accounts/goals exceed the cap.
 *
 * Read-only (no edit affordance) — the wizard's edit surface is the
 * GoalRow above. This is a roll-up confirmation surface so the advisor
 * can see "every account fully assigned, every goal fully funded"
 * without scanning per-row indicators.
 */
function AllocationMatrixPreview({
  accounts,
  goals,
}: {
  accounts: WizardDraft["accounts"];
  goals: WizardDraft["goals"];
}) {
  const { t } = useTranslation();
  if ((accounts ?? []).length === 0 || (goals ?? []).length === 0) return null;

  const visibleAccounts = (accounts ?? []).slice(0, MATRIX_DISPLAY_CAP);
  const accountOverflow = Math.max(0, (accounts ?? []).length - MATRIX_DISPLAY_CAP);
  const visibleGoals = (goals ?? []).slice(0, MATRIX_DISPLAY_CAP);
  const goalOverflow = Math.max(0, (goals ?? []).length - MATRIX_DISPLAY_CAP);

  function legAmount(goal: WizardDraft["goals"][number], accIdx: number): number | null {
    let total = 0;
    let found = false;
    for (const leg of goal.legs) {
      if (leg.account_index === accIdx) {
        const amount = Number(leg.allocated_amount);
        if (Number.isFinite(amount)) {
          total += amount;
          found = true;
        }
      }
    }
    return found ? total : null;
  }

  return (
    <div
      className="flex flex-col gap-2 border-t border-hairline pt-5"
      data-testid="allocation-matrix-preview"
    >
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("wizard.step3.matrix_title")}
      </h3>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse font-mono text-[10px]">
          <thead>
            <tr className="border-b border-hairline-2">
              <th className="px-2 py-1 text-left font-medium text-muted">
                {t("wizard.step3.matrix_header_goal")}
              </th>
              {visibleAccounts.map((acct, accIdx) => (
                <th
                  key={accIdx}
                  className="px-2 py-1 text-right font-medium text-muted"
                >
                  {`${accIdx + 1}. ${acct?.account_type ?? "?"}`}
                </th>
              ))}
              {accountOverflow > 0 && (
                <th
                  className="px-2 py-1 text-right font-medium text-muted"
                  data-testid="account-overflow"
                >
                  {t("wizard.step3.matrix_overflow_more", { count: accountOverflow })}
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {visibleGoals.map((goal, gIdx) => (
              <tr key={gIdx} className="border-b border-hairline">
                <td className="px-2 py-1 text-left text-ink">
                  {goal.name || t("wizard.step3.matrix_unnamed_goal", { index: gIdx + 1 })}
                </td>
                {visibleAccounts.map((_acct, accIdx) => {
                  const amount = legAmount(goal, accIdx);
                  return (
                    <td
                      key={accIdx}
                      className="px-2 py-1 text-right text-ink"
                      data-testid={`matrix-cell-${gIdx}-${accIdx}`}
                    >
                      {amount === null ? "—" : formatCadCompact(amount)}
                    </td>
                  );
                })}
                {accountOverflow > 0 && (
                  <td className="px-2 py-1 text-right text-muted">…</td>
                )}
              </tr>
            ))}
            {goalOverflow > 0 && (
              <tr data-testid="goal-overflow">
                <td
                  colSpan={visibleAccounts.length + (accountOverflow > 0 ? 2 : 1)}
                  className="px-2 py-1 text-left text-muted"
                >
                  {t("wizard.step3.matrix_overflow_more", { count: goalOverflow })}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GoalRow({
  index,
  onRemove,
  removable,
  accountTypes,
}: {
  index: number;
  onRemove: () => void;
  removable: boolean;
  accountTypes: string[];
}) {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const { register, control, formState } = form;
  const legs = useFieldArray({ control, name: `goals.${index}.legs` as const });
  const goalErrors = formState.errors.goals?.[index];

  return (
    <div className="border border-hairline bg-paper-2 p-4">
      <div className="grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-2">
        <input
          {...register(`goals.${index}.name` as const)}
          placeholder={t("wizard.step3.goal_name_placeholder")}
          className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
        />
        <input
          type="date"
          {...register(`goals.${index}.target_date` as const)}
          aria-label={t("wizard.step3.goal_date_label")}
          className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
        />
        <select
          {...register(`goals.${index}.necessity_score` as const, { valueAsNumber: true })}
          aria-label={t("wizard.step3.goal_necessity_label")}
          className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
        >
          <option value={5}>{t("routes.goal.tier_need")} (5)</option>
          <option value={4}>{t("routes.goal.tier_need")} (4)</option>
          <option value={3}>{t("routes.goal.tier_want")} (3)</option>
          <option value={2}>{t("routes.goal.tier_wish")} (2)</option>
          <option value={1}>{t("routes.goal.tier_wish")} (1)</option>
        </select>
        <input
          {...register(`goals.${index}.target_amount` as const)}
          placeholder={t("wizard.step3.goal_target_placeholder")}
          inputMode="decimal"
          className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onRemove}
          disabled={!removable}
          aria-label={t("wizard.step3.remove_goal")}
        >
          <Trash2 aria-hidden className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="mt-3 border-t border-hairline pt-3">
        <p className="mb-2 flex items-center justify-between font-mono text-[9px] uppercase tracking-widest text-muted">
          <span>{t("wizard.step3.legs_title")}</span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => legs.append({ account_index: 0, allocated_amount: "" })}
            aria-label={t("wizard.step3.add_leg")}
          >
            <Plus aria-hidden className="h-3 w-3" />
            <span>{t("wizard.step3.add_leg")}</span>
          </Button>
        </p>
        <div className="flex flex-col gap-1.5">
          {legs.fields.map((leg, legIdx) => (
            <div key={leg.id} className="grid grid-cols-[2fr_2fr_auto] gap-2">
              <select
                {...register(`goals.${index}.legs.${legIdx}.account_index` as const, {
                  valueAsNumber: true,
                })}
                aria-label={t("wizard.step3.leg_account_label")}
                className="border border-hairline-2 bg-paper px-3 py-1.5 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
              >
                {accountTypes.map((type, aIdx) => (
                  <option key={`${type}-${aIdx}`} value={aIdx}>
                    {`${aIdx + 1}. ${type}`}
                  </option>
                ))}
              </select>
              <input
                {...register(`goals.${index}.legs.${legIdx}.allocated_amount` as const)}
                placeholder={t("wizard.step3.leg_amount_placeholder")}
                inputMode="decimal"
                className="border border-hairline-2 bg-paper px-3 py-1.5 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => legs.remove(legIdx)}
                disabled={legs.fields.length <= 1}
                aria-label={t("wizard.step3.remove_leg")}
              >
                <Trash2 aria-hidden className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {goalErrors !== undefined && (
        <ul className="mt-2 flex flex-col gap-0.5">
          {goalErrors.name?.message !== undefined && (
            <li role="alert" className="font-mono text-[10px] text-danger">
              {goalErrors.name.message}
            </li>
          )}
          {goalErrors.target_date?.message !== undefined && (
            <li role="alert" className="font-mono text-[10px] text-danger">
              {goalErrors.target_date.message}
            </li>
          )}
          <GoalStructuredIssue
            message={goalErrors.target_amount?.message}
            testId={`goal-target-issue-${index}`}
            fallbackKey="wizard.step3.goal_target_required"
          />
          {/*
            react-hook-form wraps array-level zod issues under a
            `.root.message` sub-tree (rather than `.message` directly
            as for scalar fields). Tested live; see the structured-issue
            probe in the schema.test.ts probe harness.
          */}
          <GoalStructuredIssue
            message={
              (goalErrors.legs as { root?: { message?: string }; message?: string } | undefined)
                ?.root?.message ??
              (goalErrors.legs as { message?: string } | undefined)?.message
            }
            testId={`goal-legs-issue-${index}`}
            fallbackKey="wizard.step3.goal_legs_required"
          />
        </ul>
      )}
    </div>
  );
}

/**
 * Renders a structured zod issue produced by `schema.ts` superRefine
 * (P14 §A1.14 #16 LOCKED). Falls back to a plain-text message + a
 * stable fallback i18n key so users always see something actionable.
 */
function GoalStructuredIssue({
  message,
  testId,
  fallbackKey,
}: {
  message: string | undefined;
  testId: string;
  fallbackKey: string;
}) {
  const { t } = useTranslation();
  if (message === undefined) return null;
  const structured = parseStructuredIssue(message);
  if (structured !== null) {
    return (
      <li
        role="alert"
        data-testid={testId}
        className="font-mono text-[10px] text-danger"
      >
        {t(structured.key, structured.params)}
      </li>
    );
  }
  return (
    <li
      role="alert"
      data-testid={testId}
      className="font-mono text-[10px] text-danger"
    >
      {message || t(fallbackKey)}
    </li>
  );
}
