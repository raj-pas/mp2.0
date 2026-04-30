import { useFieldArray, useFormContext, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { type WizardDraft } from "./schema";

export function Step1Identity() {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const { register, formState, setValue, control } = form;
  const householdType = useWatch({ control, name: "household_type" });
  const members = useFieldArray({ control, name: "members" });

  function setHouseholdType(next: "single" | "couple") {
    setValue("household_type", next, { shouldDirty: true, shouldValidate: true });
    if (next === "couple" && members.fields.length === 1) {
      members.append({ name: "", dob: "" });
    } else if (next === "single" && members.fields.length === 2) {
      members.remove(1);
    }
  }

  return (
    <section
      aria-labelledby="wizard-step1-title"
      className="flex flex-col gap-5 border border-hairline-2 bg-paper p-6 shadow-sm"
    >
      <header>
        <h2
          id="wizard-step1-title"
          className="font-serif text-xl font-medium tracking-tight text-ink"
        >
          {t("wizard.step1.title")}
        </h2>
        <p className="mt-1 text-[12px] text-muted">{t("wizard.step1.subtitle")}</p>
      </header>

      <Field
        label={t("wizard.step1.name_label")}
        required
        error={formState.errors.display_name?.message}
      >
        <input
          {...register("display_name")}
          autoComplete="off"
          placeholder={t("wizard.step1.name_placeholder")}
          className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[13px] text-ink focus:border-accent focus:outline-none"
        />
      </Field>

      <Field label={t("wizard.step1.type_label")}>
        <div className="flex gap-2" role="radiogroup" aria-label={t("wizard.step1.type_label")}>
          <Button
            type="button"
            variant={householdType === "single" ? "default" : "outline"}
            size="sm"
            onClick={() => setHouseholdType("single")}
            aria-pressed={householdType === "single"}
          >
            {t("wizard.step1.type_single")}
          </Button>
          <Button
            type="button"
            variant={householdType === "couple" ? "default" : "outline"}
            size="sm"
            onClick={() => setHouseholdType("couple")}
            aria-pressed={householdType === "couple"}
          >
            {t("wizard.step1.type_couple")}
          </Button>
        </div>
      </Field>

      {householdType === "couple" && (
        <label className="flex items-start gap-2 text-[12px] text-ink">
          <input
            type="checkbox"
            {...register("joint_consent")}
            className="mt-1"
            aria-describedby="wizard-step1-consent-help"
          />
          <span>
            <span className="font-medium">{t("wizard.step1.consent_label")}</span>
            <span id="wizard-step1-consent-help" className="block text-[11px] italic text-muted">
              {t("wizard.step1.consent_help")}
            </span>
            {formState.errors.joint_consent?.message !== undefined && (
              <span role="alert" className="mt-1 block font-mono text-[10px] text-danger">
                {formState.errors.joint_consent.message}
              </span>
            )}
          </span>
        </label>
      )}

      <div className="flex flex-col gap-3">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {householdType === "couple"
            ? t("wizard.step1.members_label_couple")
            : t("wizard.step1.members_label_single")}
        </p>
        {members.fields.map((field, index) => (
          <div key={field.id} className="grid grid-cols-2 gap-3">
            <Field
              label={t("wizard.step1.member_name", { n: index + 1 })}
              error={formState.errors.members?.[index]?.name?.message}
            >
              <input
                {...register(`members.${index}.name` as const)}
                placeholder={t("wizard.step1.member_name_placeholder")}
                autoComplete="off"
                className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[13px] text-ink focus:border-accent focus:outline-none"
              />
            </Field>
            <Field
              label={t("wizard.step1.member_dob")}
              error={formState.errors.members?.[index]?.dob?.message}
            >
              <input
                type="date"
                {...register(`members.${index}.dob` as const)}
                className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-[13px] text-ink focus:border-accent focus:outline-none"
              />
            </Field>
          </div>
        ))}
      </div>

      <Field label={t("wizard.step1.notes_label")}>
        <textarea
          {...register("notes")}
          rows={3}
          maxLength={2000}
          placeholder={t("wizard.step1.notes_placeholder")}
          className="resize-y border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
        />
      </Field>
    </section>
  );
}

function Field({
  label,
  required = false,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="flex items-baseline justify-between font-mono text-[10px] uppercase tracking-widest text-muted">
        <span>{label}</span>
        {required && (
          <span aria-hidden className="text-accent-2">
            ·
          </span>
        )}
      </span>
      {children}
      {error !== undefined && (
        <span role="alert" className="font-mono text-[10px] text-danger">
          {error}
        </span>
      )}
    </label>
  );
}
