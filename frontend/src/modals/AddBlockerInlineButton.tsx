/**
 * Per-row inline "+ Add" CTA on a missing-blocker row (P3.3 / plan v20
 * §A1.33).
 *
 * Closes G5 — the MissingPanel previously was a passive list; advisors
 * had to navigate elsewhere to fix each blocker. This button lives on
 * each row, expands inline (no modal), pre-fills the canonical
 * `field_path` from `Readiness.missing[].field_path` (P8 contract), and
 * dispatches the `<FactInput>` shared control to render the right input
 * shape (date / number / enum / text). Saving fires
 * `useApplyFactOverride` with `is_added=true`; on success the row
 * disappears via Readiness re-fetch (TanStack Query invalidation
 * already wired in the hook).
 *
 * UX:
 *   - Collapsed default state shows just the "+" icon button.
 *   - Click expands the form below the row; rationale + value required
 *     (rationale ≥ 4 chars; mirrors DocDetailPanel.AddFactSection).
 *   - Cancel collapses without state loss within the panel session.
 *   - Empty `field_path` (legacy / sectionless rows) falls back to a
 *     free-form text input.
 */
import { Plus, X } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { FactInput } from "../components/FactInput";
import { useApplyFactOverride } from "../lib/review";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";

interface AddBlockerInlineButtonProps {
  workspaceId: string;
  fieldPath: string;
  label: string;
}

export function AddBlockerInlineButton({
  workspaceId,
  fieldPath,
  label,
}: AddBlockerInlineButtonProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [rationale, setRationale] = useState("");
  const apply = useApplyFactOverride(workspaceId);

  const submittable =
    fieldPath.length > 0 &&
    value.trim().length > 0 &&
    rationale.trim().length >= 4 &&
    !apply.isPending;

  function reset() {
    setValue("");
    setRationale("");
  }

  function handleCancel() {
    setOpen(false);
    reset();
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!submittable) return;
    apply.mutate(
      {
        field: fieldPath,
        value: value.trim(),
        rationale: rationale.trim(),
        is_added: true,
      },
      {
        onSuccess: () => {
          toastSuccess(
            t("review.add_blocker.saved_title"),
            t("review.add_blocker.saved_body", { label }),
          );
          setOpen(false);
          reset();
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("review.add_blocker.error"));
          toastError(t("review.add_blocker.error"), { description: e.message });
        },
      },
    );
  }

  if (!open) {
    // Compact CTA — fits in the row's right-aligned slot.
    return (
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={() => setOpen(true)}
        aria-label={t("review.add_blocker.action_aria", { label })}
        className="h-5 w-5"
        disabled={fieldPath.length === 0}
      >
        <Plus aria-hidden className="h-3 w-3 text-warning" />
      </Button>
    );
  }

  return (
    <form
      className="col-span-2 mt-1 flex flex-col gap-2 border border-warning/40 bg-paper p-2"
      onSubmit={handleSubmit}
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[9px] uppercase tracking-widest text-warning">
          {t("review.add_blocker.title", { label })}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={handleCancel}
          aria-label={t("review.add_blocker.cancel")}
          className="h-5 w-5"
        >
          <X aria-hidden className="h-3 w-3" />
        </Button>
      </div>
      {fieldPath.length > 0 && (
        <p className="font-mono text-[9px] text-muted">{fieldPath}</p>
      )}
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("review.add_blocker.value_label")}
        </span>
        <FactInput
          fieldPath={fieldPath}
          value={value}
          onChange={setValue}
          disabled={apply.isPending}
          focusOnMount
          selectPlaceholder={t("review.add_blocker.value_select_placeholder")}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("review.add_blocker.rationale_label")}
        </span>
        <textarea
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          disabled={apply.isPending}
          rows={2}
          placeholder={t("review.add_blocker.rationale_placeholder")}
          className="border border-hairline-2 bg-paper px-2 py-1 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
        />
      </label>
      <div className="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleCancel}
          disabled={apply.isPending}
        >
          {t("review.add_blocker.cancel")}
        </Button>
        <Button type="submit" size="sm" disabled={!submittable}>
          {apply.isPending
            ? t("review.add_blocker.saving")
            : t("review.add_blocker.save")}
        </Button>
      </div>
    </form>
  );
}
