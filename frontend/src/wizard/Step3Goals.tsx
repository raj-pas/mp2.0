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
import { ACCOUNT_TYPES, type WizardDraft } from "./schema";

export function Step3Goals() {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const { register, control, formState } = form;
  const accounts = useFieldArray({ control, name: "accounts" });
  const goals = useFieldArray({ control, name: "goals" });
  const accountValues = useWatch({ control, name: "accounts" });

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
              })
            }
            aria-label={t("wizard.step3.add_account")}
          >
            <Plus aria-hidden className="h-3 w-3" />
            <span>{t("wizard.step3.add_account")}</span>
          </Button>
        </div>
        <div className="flex flex-col gap-2">
          {accounts.fields.map((field, index) => (
            <div key={field.id} className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2">
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
          ))}
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
    </section>
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
          {goalErrors.target_amount?.message !== undefined && (
            <li role="alert" className="font-mono text-[10px] text-danger">
              {goalErrors.target_amount.message}
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
