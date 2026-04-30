/**
 * 5-step household wizard route — fallback path per locked decision #7.
 *
 * Doc-drop (R7) is the primary onboarding entry; this wizard handles
 * edge cases or full manual entry. The top banner offers to bounce
 * the user to `/review` if they'd rather upload documents.
 *
 * State recovery (locked decision #35): per-tab session id keys a
 * `localStorage` draft that's saved on every step transition + a
 * 30s heartbeat. On mount, if a meaningful draft is present we prompt
 * "Resume in-progress household setup?" with Resume/Discard.
 *
 * Validation: zod schema (locked decision #29). Per-step `trigger()`
 * advances only when the step's fields validate; the final commit
 * runs the full schema check.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { type FieldPath, FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";
import { useRememberedClientId } from "../chrome/ClientPicker";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { useDraftHeartbeat, useWizardDraftStore } from "./draft";
import { Step1Identity } from "./Step1Identity";
import { Step2RiskProfile } from "./Step2RiskProfile";
import { Step3Goals } from "./Step3Goals";
import { Step4External } from "./Step4External";
import { Step5Review } from "./Step5Review";
import { useWizardCommit } from "./commit";
import { draftToCommitPayload, emptyWizardDraft, wizardSchema, type WizardDraft } from "./schema";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";

type StepNumber = 1 | 2 | 3 | 4 | 5;

const STEP_FIELDS: Record<StepNumber, FieldPath<WizardDraft>[]> = {
  1: ["display_name", "household_type", "joint_consent", "members", "notes"],
  2: ["risk_profile"],
  3: ["accounts", "goals"],
  4: ["external_holdings"],
  5: [],
};

export function HouseholdWizard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const draftStore = useWizardDraftStore();
  const [, setRememberedId] = useRememberedClientId();
  const commit = useWizardCommit();

  // The recovery banner is gated by the `status === "resumable"` check
  // computed at mount time; users explicitly choose Resume or Discard.
  const [showRecoveryPrompt, setShowRecoveryPrompt] = useState(draftStore.status === "resumable");
  const [step, setStep] = useState<StepNumber>(1);

  const form = useForm<WizardDraft>({
    resolver: zodResolver(wizardSchema),
    mode: "onChange",
    defaultValues: draftStore.initialDraft,
  });

  const snapshot = useCallback(() => form.getValues(), [form]);
  useDraftHeartbeat(snapshot, draftStore.saveDraft);

  // Save on every step transition (in addition to the heartbeat).
  useEffect(() => {
    draftStore.saveDraft(form.getValues());
  }, [step, draftStore, form]);

  function discardDraft() {
    form.reset(emptyWizardDraft());
    draftStore.clearDraft();
    setShowRecoveryPrompt(false);
  }

  function keepDraft() {
    setShowRecoveryPrompt(false);
  }

  async function goNext() {
    const fields = STEP_FIELDS[step];
    const ok = fields.length === 0 ? true : await form.trigger(fields);
    if (!ok) return;
    if (step < 5) setStep((step + 1) as StepNumber);
  }

  function goBack() {
    if (step > 1) setStep((step - 1) as StepNumber);
  }

  async function onSubmit() {
    const ok = await form.trigger();
    if (!ok) return;
    const draft = form.getValues();
    // Strip empty external-holding rows (locked decision #19 supports
    // optional step 4) before POSTing.
    const cleaned: WizardDraft = {
      ...draft,
      external_holdings: (draft.external_holdings ?? []).filter(
        (row) => row.value !== undefined && row.value.trim().length > 0,
      ),
    };
    commit.mutate(draftToCommitPayload(cleaned), {
      onSuccess: (response) => {
        draftStore.clearDraft();
        setRememberedId(response.household_id);
        toastSuccess(t("wizard.commit.success_title"), t("wizard.commit.success_body"));
        navigate("/");
      },
      onError: (err) => {
        const e = normalizeApiError(err, t("wizard.commit.error_generic"));
        toastError(t("wizard.commit.error_generic"), { description: e.message });
      },
    });
  }

  return (
    <ErrorBoundary scope="wizard">
      <main className="flex flex-1 flex-col gap-4 overflow-y-auto bg-paper p-6">
        <Banner onDocDrop={() => navigate("/review")} />

        {showRecoveryPrompt && <RecoveryBanner onResume={keepDraft} onDiscard={discardDraft} />}

        <Stepper currentStep={step} />

        <FormProvider {...form}>
          {step === 1 && <Step1Identity />}
          {step === 2 && <Step2RiskProfile />}
          {step === 3 && <Step3Goals />}
          {step === 4 && <Step4External />}
          {step === 5 && <Step5Review />}
        </FormProvider>

        <nav className="flex items-center justify-between border-t border-hairline pt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={goBack}
            disabled={step === 1 || commit.isPending}
          >
            <ChevronLeft aria-hidden className="h-3 w-3" />
            <span>{t("wizard.nav.back")}</span>
          </Button>
          {step < 5 ? (
            <Button type="button" size="sm" onClick={goNext} disabled={commit.isPending}>
              <span>{t("wizard.nav.next")}</span>
              <ChevronRight aria-hidden className="h-3 w-3" />
            </Button>
          ) : (
            <Button type="button" size="sm" onClick={onSubmit} disabled={commit.isPending}>
              {commit.isPending ? t("wizard.nav.committing") : t("wizard.nav.commit")}
            </Button>
          )}
        </nav>
      </main>
    </ErrorBoundary>
  );
}

function Banner({ onDocDrop }: { onDocDrop: () => void }) {
  const { t } = useTranslation();
  return (
    <aside className="flex items-start gap-3 border border-accent-2/40 bg-paper-2 p-3">
      <FileText aria-hidden className="mt-0.5 h-4 w-4 text-accent-2" />
      <div className="flex-1">
        <p className="font-sans text-[12px] text-ink">
          <strong>{t("wizard.banner.bold")}</strong> {t("wizard.banner.body")}
        </p>
      </div>
      <Button type="button" variant="outline" size="sm" onClick={onDocDrop}>
        {t("wizard.banner.docs_cta")}
      </Button>
    </aside>
  );
}

function RecoveryBanner({ onResume, onDiscard }: { onResume: () => void; onDiscard: () => void }) {
  const { t } = useTranslation();
  return (
    <aside
      role="alertdialog"
      aria-labelledby="wizard-recovery-title"
      className="flex items-start gap-3 border border-ink bg-paper-2 p-3"
    >
      <div className="flex-1">
        <p
          id="wizard-recovery-title"
          className="font-mono text-[10px] uppercase tracking-widest text-ink"
        >
          {t("wizard.recovery.title")}
        </p>
        <p className="mt-0.5 text-[12px] text-muted">{t("wizard.recovery.body")}</p>
      </div>
      <Button type="button" variant="default" size="sm" onClick={onResume}>
        {t("wizard.recovery.resume")}
      </Button>
      <Button type="button" variant="outline" size="sm" onClick={onDiscard}>
        {t("wizard.recovery.discard")}
      </Button>
    </aside>
  );
}

function Stepper({ currentStep }: { currentStep: StepNumber }) {
  const { t } = useTranslation();
  const stepLabels = useMemo(
    () => [
      t("wizard.step1.title"),
      t("wizard.step2.title"),
      t("wizard.step3.title"),
      t("wizard.step4.title"),
      t("wizard.step5.title"),
    ],
    [t],
  );
  return (
    <ol className="flex items-center gap-1 border border-hairline bg-paper-2 p-2">
      {stepLabels.map((label, index) => {
        const stepNum = (index + 1) as StepNumber;
        const isCurrent = stepNum === currentStep;
        const isDone = stepNum < currentStep;
        return (
          <li
            key={label}
            aria-current={isCurrent ? "step" : undefined}
            className={cn(
              "flex flex-1 items-center gap-2 px-3 py-1.5",
              isCurrent ? "bg-ink text-paper" : isDone ? "text-ink" : "text-muted",
            )}
          >
            <span className="font-mono text-[10px] uppercase tracking-widest">{stepNum}</span>
            <span className="font-sans text-[12px]">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
