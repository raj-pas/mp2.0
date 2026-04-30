/**
 * Wizard step 2 — household risk profile (Q1-Q4).
 *
 * Per locked decision #6, the panel exposes T (0-100) + C (0-100)
 * + anchor (0-50) as advisor-transparent intermediates here (the
 * canon §4.2 methodology is on display in the wizard) — but every
 * downstream surface (RiskSlider on goals, descriptors elsewhere)
 * uses canon 1-5 + descriptor only. The wizard is the ONE place
 * where those numbers are visible.
 *
 * Live recompute via `useRiskProfilePreview` (locked decision #2,
 * server roundtrip on every interaction) with `useDebouncedValue`
 * upstream of the query key (locked decision #18 latency budget).
 */
import { useMemo } from "react";
import { Controller, useFormContext, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { useDebouncedValue } from "../lib/debounce";
import { type RiskProfileRequest, useRiskProfilePreview } from "../lib/preview";
import { Q3_STRESSORS, type WizardDraft } from "./schema";
import { cn } from "../lib/cn";

export function Step2RiskProfile() {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const { register, control, formState } = form;
  const profile = useWatch({ control, name: "risk_profile" });
  const debouncedProfile = useDebouncedValue<RiskProfileRequest>(
    {
      q1: Number(profile.q1) || 0,
      q2: profile.q2,
      q3: profile.q3,
      q4: profile.q4,
    },
    250,
  );
  const preview = useRiskProfilePreview(debouncedProfile);

  return (
    <section aria-labelledby="wizard-step2-title" className="grid grid-cols-[1fr_280px] gap-5">
      <div className="flex flex-col gap-5 border border-hairline-2 bg-paper p-6 shadow-sm">
        <header>
          <h2
            id="wizard-step2-title"
            className="font-serif text-xl font-medium tracking-tight text-ink"
          >
            {t("wizard.step2.title")}
          </h2>
          <p className="mt-1 text-[12px] text-muted">{t("wizard.step2.subtitle")}</p>
        </header>

        <Question id="q1" tag="Tolerance" question={t("wizard.step2.q1_text")}>
          <Controller
            control={control}
            name="risk_profile.q1"
            render={({ field }) => (
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={10}
                  step={1}
                  value={field.value}
                  onChange={(e) => field.onChange(Number(e.target.value))}
                  aria-valuemin={0}
                  aria-valuemax={10}
                  aria-valuenow={field.value}
                  aria-label={t("wizard.step2.q1_text")}
                  className="flex-1"
                />
                <span className="w-10 text-right font-mono text-[12px] text-ink">
                  {field.value}
                </span>
              </div>
            )}
          />
          <p className="font-mono text-[9px] uppercase tracking-widest text-muted">
            {t("wizard.step2.q1_legend")}
          </p>
        </Question>

        <Question id="q2" tag="Stress response" question={t("wizard.step2.q2_text")}>
          <Controller
            control={control}
            name="risk_profile.q2"
            render={({ field }) => (
              <ChoiceRow
                value={field.value}
                onChange={field.onChange}
                options={[
                  { value: "A", label: t("wizard.step2.q2_a") },
                  { value: "B", label: t("wizard.step2.q2_b") },
                  { value: "C", label: t("wizard.step2.q2_c") },
                  { value: "D", label: t("wizard.step2.q2_d") },
                ]}
              />
            )}
          />
        </Question>

        <Question id="q3" tag="Stressors" question={t("wizard.step2.q3_text")}>
          <Controller
            control={control}
            name="risk_profile.q3"
            render={({ field }) => (
              <div className="flex flex-wrap gap-2">
                {Q3_STRESSORS.map((code) => {
                  const checked = field.value.includes(code);
                  return (
                    <label
                      key={code}
                      className={cn(
                        "flex cursor-pointer items-center gap-2 border px-3 py-1.5 font-sans text-[12px]",
                        checked
                          ? "border-ink bg-paper-2 text-ink"
                          : "border-hairline bg-paper text-muted hover:border-ink/40",
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          const next = checked
                            ? field.value.filter((c: string) => c !== code)
                            : [...field.value, code];
                          field.onChange(next);
                        }}
                        className="sr-only"
                      />
                      {t(`wizard.step2.q3_${code}`)}
                    </label>
                  );
                })}
              </div>
            )}
          />
        </Question>

        <Question id="q4" tag="Capacity" question={t("wizard.step2.q4_text")}>
          <Controller
            control={control}
            name="risk_profile.q4"
            render={({ field }) => (
              <ChoiceRow
                value={field.value}
                onChange={field.onChange}
                options={[
                  { value: "A", label: t("wizard.step2.q4_a") },
                  { value: "B", label: t("wizard.step2.q4_b") },
                  { value: "C", label: t("wizard.step2.q4_c") },
                  { value: "D", label: t("wizard.step2.q4_d") },
                ]}
              />
            )}
          />
        </Question>

        <p className="sr-only">
          {/* register q-fields so RHF tracks them even though we use Controller */}
          <input type="hidden" {...register("risk_profile.q1", { valueAsNumber: true })} />
        </p>
      </div>

      <PreviewPanel loading={preview.isPending} error={preview.isError} data={preview.data} />

      {formState.errors.risk_profile?.message !== undefined && (
        <p role="alert" className="col-span-2 font-mono text-[10px] text-danger">
          {formState.errors.risk_profile.message}
        </p>
      )}
    </section>
  );
}

function PreviewPanel({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: boolean;
  data: ReturnType<typeof useRiskProfilePreview>["data"];
}) {
  const { t } = useTranslation();
  return (
    <aside
      aria-label={t("wizard.step2.preview_title")}
      className="flex flex-col gap-4 border border-hairline-2 bg-paper-2 p-5"
    >
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("wizard.step2.preview_title")}
      </h3>
      {loading && <Skeleton className="h-32 w-full" />}
      {error && (
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("errors.preview_failed")}
        </p>
      )}
      {!loading && !error && data !== undefined && (
        <dl className="flex flex-col gap-3">
          <Stat
            label={t("wizard.step2.preview_t")}
            value={data.tolerance_score.toFixed(0)}
            suffix="/100"
          />
          <Stat
            label={t("wizard.step2.preview_c")}
            value={data.capacity_score.toFixed(0)}
            suffix="/100"
          />
          <Stat
            label={t("wizard.step2.preview_anchor")}
            value={data.anchor.toFixed(1)}
            suffix="/50"
          />
          <Stat label={t("wizard.step2.preview_descriptor")} value={data.household_descriptor} />
          <Stat label={t("wizard.step2.preview_canon_score")} value={`${data.score_1_5} / 5`} />
        </dl>
      )}
    </aside>
  );
}

function Stat({ label, value, suffix }: { label: string; value: string; suffix?: string }) {
  return (
    <div className="flex flex-col">
      <dt className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</dt>
      <dd className="font-serif text-lg font-medium text-ink">
        {value}
        {suffix !== undefined && <span className="ml-1 text-[10px] text-muted">{suffix}</span>}
      </dd>
    </div>
  );
}

function Question({
  id,
  tag,
  question,
  children,
}: {
  id: string;
  tag: string;
  question: string;
  children: React.ReactNode;
}) {
  const tagId = useMemo(() => `wizard-step2-${id}-tag`, [id]);
  return (
    <fieldset className="flex flex-col gap-2 border-t border-hairline pt-4 first-of-type:border-t-0 first-of-type:pt-0">
      <legend className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-muted">
        <span id={tagId}>{id.toUpperCase()}</span>
        <span aria-hidden className="text-accent-2">
          ·
        </span>
        <span>{tag}</span>
      </legend>
      <p className="font-sans text-[13px] text-ink">{question}</p>
      <div className="mt-1">{children}</div>
    </fieldset>
  );
}

function ChoiceRow<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (next: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "flex flex-col items-start gap-1 border px-3 py-2 text-left transition-colors",
              active
                ? "border-ink bg-ink text-paper"
                : "border-hairline bg-paper text-ink hover:border-ink/40",
            )}
          >
            <span className="font-mono text-[10px] uppercase tracking-widest opacity-70">
              {opt.value}
            </span>
            <span className="font-sans text-[12px]">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
