/**
 * Wizard step 4 — external holdings (optional).
 *
 * Each row's asset percentages must sum to 100; client-side
 * validation mirrors the server's `WizardExternalHoldingSerializer`
 * superRefine. This step is skippable per the plan — empty rows are
 * stripped at commit time by the parent wizard.
 */
import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, useFormContext, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { type WizardDraft } from "./schema";
import { cn } from "../lib/cn";

export function Step4External() {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const { register, control, formState } = form;
  const holdings = useFieldArray({ control, name: "external_holdings" });
  const watched = useWatch({ control, name: "external_holdings" });

  return (
    <section
      aria-labelledby="wizard-step4-title"
      className="flex flex-col gap-5 border border-hairline-2 bg-paper p-6 shadow-sm"
    >
      <header className="flex items-start justify-between">
        <div>
          <h2
            id="wizard-step4-title"
            className="font-serif text-xl font-medium tracking-tight text-ink"
          >
            {t("wizard.step4.title")}
          </h2>
          <p className="mt-1 text-[12px] text-muted">{t("wizard.step4.subtitle")}</p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() =>
            holdings.append({
              name: "",
              value: "",
              equity_pct: "0",
              fixed_income_pct: "0",
              cash_pct: "0",
              real_assets_pct: "0",
            })
          }
          aria-label={t("wizard.step4.add_holding")}
        >
          <Plus aria-hidden className="h-3 w-3" />
          <span>{t("wizard.step4.add_holding")}</span>
        </Button>
      </header>

      {holdings.fields.length === 0 ? (
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("wizard.step4.empty")}
        </p>
      ) : (
        <table className="w-full table-fixed text-left">
          <thead>
            <tr>
              <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
                {t("wizard.step4.col_name")}
              </th>
              <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
                {t("wizard.step4.col_value")}
              </th>
              <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
                {t("wizard.step4.col_equity")}
              </th>
              <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
                {t("wizard.step4.col_fixed")}
              </th>
              <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
                {t("wizard.step4.col_cash")}
              </th>
              <th className="pb-2 font-mono text-[9px] uppercase tracking-widest text-muted">
                {t("wizard.step4.col_real")}
              </th>
              <th className="pb-2 text-right font-mono text-[9px] uppercase tracking-widest text-muted">
                Σ
              </th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {holdings.fields.map((field, index) => {
              const row = watched?.[index];
              const sum =
                Number(row?.equity_pct ?? 0) +
                Number(row?.fixed_income_pct ?? 0) +
                Number(row?.cash_pct ?? 0) +
                Number(row?.real_assets_pct ?? 0);
              const sumOk = Math.abs(sum - 100) < 0.01;
              const error = formState.errors.external_holdings?.[index];
              return (
                <tr key={field.id} className="border-t border-hairline">
                  <td className="py-1.5">
                    <input
                      {...register(`external_holdings.${index}.name` as const)}
                      placeholder={t("wizard.step4.name_placeholder")}
                      className="w-full border border-hairline-2 bg-paper px-2 py-1.5 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
                    />
                  </td>
                  <td className="py-1.5">
                    <input
                      {...register(`external_holdings.${index}.value` as const)}
                      placeholder="50000"
                      inputMode="decimal"
                      className="w-full border border-hairline-2 bg-paper px-2 py-1.5 font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
                    />
                  </td>
                  <PctCell name={`external_holdings.${index}.equity_pct`} register={register} />
                  <PctCell
                    name={`external_holdings.${index}.fixed_income_pct`}
                    register={register}
                  />
                  <PctCell name={`external_holdings.${index}.cash_pct`} register={register} />
                  <PctCell
                    name={`external_holdings.${index}.real_assets_pct`}
                    register={register}
                  />
                  <td
                    className={cn(
                      "py-1.5 text-right font-mono text-[11px]",
                      sumOk ? "text-success" : "text-danger",
                    )}
                  >
                    {sum.toFixed(0)}
                  </td>
                  <td className="py-1.5 text-right">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => holdings.remove(index)}
                      aria-label={t("wizard.step4.remove_holding")}
                    >
                      <Trash2 aria-hidden className="h-3 w-3" />
                    </Button>
                    {error?.equity_pct?.message !== undefined && (
                      <span role="alert" className="block font-mono text-[9px] text-danger">
                        {error.equity_pct.message}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}

function PctCell({
  name,
  register,
}: {
  name: `external_holdings.${number}.${"equity_pct" | "fixed_income_pct" | "cash_pct" | "real_assets_pct"}`;
  register: ReturnType<typeof useFormContext<WizardDraft>>["register"];
}) {
  return (
    <td className="py-1.5">
      <input
        {...register(name)}
        placeholder="0"
        inputMode="decimal"
        className="w-full border border-hairline-2 bg-paper px-2 py-1.5 text-right font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
      />
    </td>
  );
}
