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
import { Check, ChevronLeft, ChevronRight, FileText, Save, X } from "lucide-react";
import { type KeyboardEvent, useCallback, useEffect, useMemo, useState } from "react";
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

/**
 * Step 3 hard-block gate (P14 §A1.14 #5 + #16 LOCKED).
 *
 * Continue is disabled when EITHER:
 *   - any account-centric superRefine issue exists at
 *     `accounts.<i>.current_value` (sum of legs ≠ account value), OR
 *   - any goal-side superRefine issue exists at
 *     `goals.<i>.target_amount` or `goals.<i>.legs` (zero legs / no target).
 *
 * Mirrors the backend portfolio-readiness gate exactly. Eliminates the
 * schema-mismatch failure mode that prompted G14 (advisor commits a
 * partially-allocated household; engine refuses to generate post-commit).
 */
function hasStep3HardBlockError(
  errors: ReturnType<typeof useForm<WizardDraft>>["formState"]["errors"],
): boolean {
  const accountErrors = errors.accounts;
  if (Array.isArray(accountErrors)) {
    for (const err of accountErrors) {
      if (err?.current_value?.message !== undefined) return true;
    }
  }
  const goalErrors = errors.goals;
  if (Array.isArray(goalErrors)) {
    for (const err of goalErrors) {
      if (err?.target_amount?.message !== undefined) return true;
      if (err?.legs !== undefined) {
        // legs may have:
        //   - `.root.message` (array-level superRefine emission;
        //     react-hook-form wraps array-level errors under .root)
        //   - `.message` (alternative shape some zod issues take)
        //   - per-leg child errors as array elements
        // Any one of these constitutes a hard-block.
        const legs = err.legs as {
          root?: { message?: string };
          message?: string;
        } & Array<unknown>;
        if (legs.root?.message !== undefined) return true;
        if (legs.message !== undefined) return true;
        if (Array.isArray(legs) && legs.length > 0) return true;
      }
    }
  }
  return false;
}

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

  function dismissRecoveryBanner() {
    // "Clearable affordance" — close the banner without committing
    // to either resume or discard. The localStorage draft remains
    // intact; the form keeps whatever is currently in state.
    setShowRecoveryPrompt(false);
  }

  function handleSaveDraft() {
    const savedAt = draftStore.saveDraft(form.getValues());
    const formatted = formatSavedTimestamp(savedAt);
    toastSuccess(
      t("polish_b.wizard.draft_saved_title"),
      t("polish_b.wizard.draft_saved_body", { timestamp: formatted }),
    );
  }

  async function goNext() {
    const fields = STEP_FIELDS[step];
    const ok = fields.length === 0 ? true : await form.trigger(fields);
    if (!ok) return;
    // P14 hard-block (§A1.14 #5 + #16): Continue cannot advance from
    // Step 3 if any account-centric or goal-side invariant fails. The
    // button itself is disabled below; this is a defense-in-depth
    // check in case `trigger()` misses an issue (e.g. when the user
    // just edited a leg but the debounced superRefine hasn't fired
    // yet).
    if (step === 3 && hasStep3HardBlockError(form.formState.errors)) return;
    if (step < 5) setStep((step + 1) as StepNumber);
  }

  function goBack() {
    if (step > 1) setStep((step - 1) as StepNumber);
  }

  function jumpToStep(target: StepNumber) {
    // Step circles are keyboard-navigable; we permit jumping back to
    // any already-completed step (target < step) without re-validating
    // since the existing step's data has already been validated. We
    // do NOT permit forward jumps — the underlying step navigation
    // logic still runs through goNext()'s per-step trigger().
    if (target < step) setStep(target);
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
        // Per locked decision (this session): if the just-committed
        // household has outstanding readiness blockers, surface a
        // WARNING toast instead of plain success so the advisor knows
        // to follow up. The persistent inline panel on the household
        // route (HouseholdPortfolioPanel cold-start) renders the same
        // list — toast is the in-flight signal; panel is the durable
        // one. We still navigate (commit is non-reversible at this
        // point + advisor needs to land on the household to fix gaps).
        const blockers = response.readiness_blockers ?? [];
        if (blockers.length > 0) {
          toastError(t("wizard.commit.warn_blockers_title"), {
            description: t("wizard.commit.warn_blockers_body", {
              count: blockers.length,
            }),
          });
        } else {
          toastSuccess(t("wizard.commit.success_title"), t("wizard.commit.success_body"));
        }
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

        {showRecoveryPrompt && (
          <RecoveryBanner
            savedAt={draftStore.initialSavedAt}
            onResume={keepDraft}
            onDiscard={discardDraft}
            onDismiss={dismissRecoveryBanner}
          />
        )}

        <Stepper currentStep={step} onJumpToStep={jumpToStep} />

        <FormProvider {...form}>
          {step === 1 && <Step1Identity />}
          {step === 2 && <Step2RiskProfile />}
          {step === 3 && <Step3Goals />}
          {step === 4 && <Step4External />}
          {step === 5 && <Step5Review />}
        </FormProvider>

        <nav className="flex items-center justify-between gap-2 border-t border-hairline pt-4">
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
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleSaveDraft}
              disabled={commit.isPending}
              aria-label={t("polish_b.wizard.save_draft_aria")}
            >
              <Save aria-hidden className="h-3 w-3" />
              <span>{t("polish_b.wizard.save_draft")}</span>
            </Button>
            {step < 5 ? (
              <Button
                type="button"
                size="sm"
                onClick={goNext}
                disabled={
                  commit.isPending ||
                  // P14 hard-block (§A1.14 #5 + #16 LOCKED): Continue
                  // literally disabled when Step 3 invariants fail.
                  (step === 3 && hasStep3HardBlockError(form.formState.errors))
                }
              >
                <span>{t("wizard.nav.next")}</span>
                <ChevronRight aria-hidden className="h-3 w-3" />
              </Button>
            ) : (
              <Button type="button" size="sm" onClick={onSubmit} disabled={commit.isPending}>
                {commit.isPending ? t("wizard.nav.committing") : t("wizard.nav.commit")}
              </Button>
            )}
          </div>
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

function RecoveryBanner({
  savedAt,
  onResume,
  onDiscard,
  onDismiss,
}: {
  savedAt: string | null;
  onResume: () => void;
  onDiscard: () => void;
  onDismiss: () => void;
}) {
  const { t } = useTranslation();
  const subtitle =
    savedAt !== null
      ? t("polish_b.wizard.recovery_saved_at", { timestamp: formatSavedTimestamp(savedAt) })
      : t("wizard.recovery.body");
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
          {t("polish_b.wizard.recovery_title")}
        </p>
        <p className="mt-0.5 text-[12px] text-muted">{subtitle}</p>
      </div>
      <Button type="button" variant="default" size="sm" onClick={onResume}>
        {t("polish_b.wizard.recovery_resume")}
      </Button>
      <Button type="button" variant="outline" size="sm" onClick={onDiscard}>
        {t("wizard.recovery.discard")}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onDismiss}
        aria-label={t("polish_b.wizard.recovery_dismiss_aria")}
      >
        <X aria-hidden className="h-3.5 w-3.5" />
      </Button>
    </aside>
  );
}

const TOTAL_STEPS = 5;

function Stepper({
  currentStep,
  onJumpToStep,
}: {
  currentStep: StepNumber;
  onJumpToStep: (target: StepNumber) => void;
}) {
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

  // Progress fraction for the thin connector line: full at the last
  // completed step, plus a partial fill into the current step. We use
  // (currentStep - 1) / (TOTAL_STEPS - 1) — a simple discrete bar that
  // fills as the advisor advances.
  const progressPct = ((currentStep - 1) / (TOTAL_STEPS - 1)) * 100;

  function onCircleKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    stepNum: StepNumber,
    isPrior: boolean,
  ) {
    if (!isPrior) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onJumpToStep(stepNum);
    }
  }

  return (
    <div className="flex flex-col gap-2 border border-hairline bg-paper-2 p-3">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("polish_b.wizard.step_indicator", { current: currentStep, total: TOTAL_STEPS })}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-widest text-ink">
          {stepLabels[currentStep - 1]}
        </span>
      </div>
      <div className="relative">
        <div
          aria-hidden
          className="absolute left-3 right-3 top-3 h-px bg-hairline-2"
        />
        <div
          aria-hidden
          className="absolute left-3 top-3 h-px bg-accent motion-safe:transition-[width] motion-safe:duration-300"
          style={{ width: `calc((100% - 24px) * ${progressPct} / 100)` }}
        />
        <ol
          className="relative flex items-start justify-between"
          aria-label={t("polish_b.wizard.stepper_aria")}
        >
          {stepLabels.map((label, index) => {
            const stepNum = (index + 1) as StepNumber;
            const isCurrent = stepNum === currentStep;
            const isDone = stepNum < currentStep;
            const isPrior = isDone;
            return (
              <li
                key={label}
                aria-current={isCurrent ? "step" : undefined}
                className="flex flex-1 flex-col items-center gap-1.5"
              >
                <button
                  type="button"
                  onClick={() => isPrior && onJumpToStep(stepNum)}
                  onKeyDown={(e) => onCircleKeyDown(e, stepNum, isPrior)}
                  disabled={!isPrior}
                  aria-label={t("polish_b.wizard.step_circle_aria", {
                    step: stepNum,
                    total: TOTAL_STEPS,
                    label,
                  })}
                  className={cn(
                    "flex h-6 w-6 items-center justify-center border font-mono text-[10px]",
                    "motion-safe:transition-colors motion-safe:duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-paper-2",
                    isCurrent
                      ? "border-accent bg-accent text-ink"
                      : isDone
                        ? "border-accent bg-paper text-accent hover:bg-accent/10"
                        : "border-hairline-2 bg-paper text-muted",
                    !isPrior && "cursor-default",
                  )}
                >
                  {isDone ? (
                    <Check aria-hidden className="h-3 w-3" />
                  ) : (
                    <span>{stepNum}</span>
                  )}
                </button>
                <span
                  className={cn(
                    "font-sans text-[11px]",
                    isCurrent ? "text-ink" : isDone ? "text-ink" : "text-muted",
                  )}
                >
                  {label}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}

function formatSavedTimestamp(iso: string): string {
  // Locale-aware short time/date for the toast + recovery banner.
  // Falls back to the raw ISO string if Date parsing fails (defensive
  // — localStorage payloads can be tampered with).
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      hour: "numeric",
      minute: "2-digit",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}
