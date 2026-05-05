/**
 * Bulk "Resolve all N missing fields" wizard (P3.3 / plan v20 §A1.33;
 * Round 8 #5 — auto-suggested at N≥4).
 *
 * Closes G6 — when an advisor faces ≥4 missing blockers, fixing them
 * one-by-one via the inline `<AddBlockerInlineButton>` is a friction
 * trap. This wizard collects them into a stepped flow:
 *
 *   - One field per step; the canonical `field_path` from
 *     `Readiness.missing[].field_path` (P8) drives the `<FactInput>`
 *     shape (date/number/enum/text).
 *   - Save-and-next on each step; the next step picks up after a
 *     readiness re-fetch (TanStack Query invalidation already wired
 *     into `useApplyFactOverride.onSuccess`).
 *   - Skip-allowed per step (closes the wizard's grip without losing
 *     the advisor's session — they can always reopen it).
 *   - "Continue later" exits without losing progress; the saved fields
 *     persist as `FactOverride` rows server-side.
 *
 * Lazy-loaded per §A1.20 (the wizard's render path is cold for most
 * sessions). The chunk lands as `ResolveAllMissingWizard-*.js` via
 * Vite's default chunk naming, and the parent `MissingPanel` wraps
 * the dynamic import in a `<Suspense>` boundary.
 *
 * Accessibility:
 *   - aria-modal=true on the root <aside> (per anti-pattern #12).
 *   - Imperative Esc handler mirrors `DocDetailPanel.tsx:56-67` —
 *     Radix's Dialog primitive ALSO ships Esc, but anti-pattern #12
 *     codifies "always wire your own Esc when aria-modal=true" so the
 *     contract is explicit and survives Radix major-version churn.
 *   - Focus moves to the close button on open; Tab cycles inside the
 *     dialog naturally (no focus-trap library needed for the simple
 *     button + form layout).
 */
import { X } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { FactInput } from "../components/FactInput";
import {
  type ReadinessRow,
  useApplyFactOverride,
  useReviewWorkspace,
} from "../lib/review";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";

interface ResolveAllMissingWizardProps {
  workspaceId: string;
  initialMissing: ReadinessRow[];
  onClose: () => void;
}

/**
 * Default export — required so the parent's `React.lazy(() =>
 * import("./ResolveAllMissingWizard"))` can resolve to the component.
 */
export default function ResolveAllMissingWizard({
  workspaceId,
  initialMissing,
  onClose,
}: ResolveAllMissingWizardProps) {
  const { t } = useTranslation();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const apply = useApplyFactOverride(workspaceId);
  const workspaceQuery = useReviewWorkspace(workspaceId);

  // Live missing rows: prefer the workspace's freshly-polled readiness
  // (re-fetch happens between steps because the override mutation
  // invalidates the workspace query). Fall back to the initial snapshot
  // so the first frame renders immediately without a flicker.
  const missing: ReadinessRow[] = useMemo(() => {
    const live = workspaceQuery.data?.readiness?.missing;
    if (Array.isArray(live)) return live;
    return initialMissing;
  }, [workspaceQuery.data, initialMissing]);

  // Step pointer over the canonical-path-bearing rows. Skip-allowed
  // means we always advance past the current row by index, never by
  // re-querying for the "first remaining" row — otherwise a skipped
  // row would auto-snap back into place after the next refresh.
  const [stepIndex, setStepIndex] = useState(0);
  const [value, setValue] = useState("");
  const [rationale, setRationale] = useState("");

  const eligibleRows = useMemo(
    () => missing.filter((row) => (row.field_path ?? "").length > 0),
    [missing],
  );
  const currentRow = eligibleRows[stepIndex] ?? null;
  const totalSteps = eligibleRows.length;

  // Imperative Esc handler — anti-pattern #12 per the locked decision
  // log: aria-modal=true REQUIRES its own Esc binding. Mirror the
  // sibling DocDetailPanel pattern verbatim.
  useEffect(() => {
    closeButtonRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  // Reset the per-step inputs when the step pointer or row changes.
  useEffect(() => {
    setValue("");
    setRationale("");
  }, [stepIndex, currentRow?.field_path]);

  function handleSkip() {
    setStepIndex((i) => i + 1);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!currentRow || (currentRow.field_path ?? "").length === 0) return;
    if (value.trim().length === 0 || rationale.trim().length < 4) return;
    apply.mutate(
      {
        field: currentRow.field_path ?? "",
        value: value.trim(),
        rationale: rationale.trim(),
        is_added: true,
      },
      {
        onSuccess: () => {
          toastSuccess(
            t("review.resolve_wizard.step_saved_title"),
            t("review.resolve_wizard.step_saved_body", {
              label: currentRow.label,
            }),
          );
          // Advance — readiness re-fetches via the hook's invalidation
          // and the `missing` memo picks up the next step's row.
          setStepIndex((i) => i + 1);
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("review.resolve_wizard.error"));
          toastError(t("review.resolve_wizard.error"), { description: e.message });
        },
      },
    );
  }

  const allDone = totalSteps === 0 || stepIndex >= totalSteps;
  const submittable =
    !apply.isPending &&
    currentRow !== null &&
    value.trim().length > 0 &&
    rationale.trim().length >= 4;

  return (
    <>
      {/* Backdrop — click closes; same opacity as DocDetailPanel so
          the parent ReviewScreen still reads as the page context. */}
      <div
        aria-hidden
        onClick={onClose}
        className="fixed inset-0 z-40 bg-ink/30"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="resolve-wizard-title"
        className={cn(
          "fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[min(92vw,560px)]",
          "-translate-x-1/2 -translate-y-1/2 flex-col overflow-y-auto",
          "border border-hairline-2 bg-paper shadow-xl",
          "motion-safe:animate-[fadeIn_180ms_ease-out]",
        )}
      >
        <header className="flex items-baseline justify-between border-b border-hairline-2 px-4 py-3">
          <div className="flex flex-col">
            <h2
              id="resolve-wizard-title"
              className="font-serif text-base font-medium tracking-tight text-ink"
            >
              {t("review.resolve_wizard.title")}
            </h2>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {allDone
                ? t("review.resolve_wizard.progress_done")
                : t("review.resolve_wizard.progress", {
                    current: stepIndex + 1,
                    total: totalSteps,
                  })}
            </p>
          </div>
          <Button
            ref={closeButtonRef}
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("review.resolve_wizard.continue_later")}
          >
            <X aria-hidden className="h-4 w-4" />
          </Button>
        </header>

        <div className="flex flex-1 flex-col gap-4 p-4">
          {allDone ? (
            <div className="flex flex-col gap-3">
              <p className="font-sans text-[12px] text-ink">
                {t("review.resolve_wizard.all_done_body")}
              </p>
              <Button type="button" size="sm" onClick={onClose} className="self-end">
                {t("review.resolve_wizard.close")}
              </Button>
            </div>
          ) : (
            <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
                  {t("review.resolve_wizard.section")}
                </span>
                <span className="font-sans text-[14px] text-ink">
                  {currentRow?.label ?? "—"}
                </span>
                {currentRow?.field_path && (
                  <span className="font-mono text-[10px] text-muted">
                    {currentRow.field_path}
                  </span>
                )}
              </div>
              <label className="flex flex-col gap-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
                  {t("review.resolve_wizard.value_label")}
                </span>
                <FactInput
                  fieldPath={currentRow?.field_path ?? ""}
                  value={value}
                  onChange={setValue}
                  disabled={apply.isPending}
                  focusOnMount
                  selectPlaceholder={t("review.resolve_wizard.value_select_placeholder")}
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
                  {t("review.resolve_wizard.rationale_label")}
                </span>
                <textarea
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  disabled={apply.isPending}
                  rows={2}
                  placeholder={t("review.resolve_wizard.rationale_placeholder")}
                  className="border border-hairline-2 bg-paper px-2 py-1 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
                />
              </label>
              <div className="flex items-center justify-between gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={onClose}
                  disabled={apply.isPending}
                >
                  {t("review.resolve_wizard.continue_later")}
                </Button>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleSkip}
                    disabled={apply.isPending}
                  >
                    {t("review.resolve_wizard.skip")}
                  </Button>
                  <Button type="submit" size="sm" disabled={!submittable}>
                    {apply.isPending
                      ? t("review.resolve_wizard.saving")
                      : t("review.resolve_wizard.save_and_next")}
                  </Button>
                </div>
              </div>
            </form>
          )}
        </div>
      </aside>
    </>
  );
}
