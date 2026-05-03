/**
 * Feedback button + modal (Phase 5b.1, locked 2026-05-02).
 *
 * Backend persists the row to a Feedback model; ops triages from
 * GET /api/feedback/report/ (analyst-only). No runtime Linear API
 * call; the schema mirrors what Linear's `save_issue` MCP would
 * consume so a future automated-sync migration is a serializer +
 * cron task.
 *
 * Real-PII discipline: we auto-include the route + session_id +
 * browser_user_agent (low-PII context), but NEVER the workspace_id
 * or fact values. The advisor narrates what happened in their own
 * words.
 */
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { useSubmitFeedback } from "../lib/auth";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";

type Severity = "blocking" | "friction" | "suggestion";

export function FeedbackButton() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen(true)}
        aria-label={t("chrome.feedback.open_label")}
      >
        {t("chrome.feedback.button")}
      </Button>
      {open && (
        <FeedbackModal onClose={() => setOpen(false)} onSubmitted={() => setOpen(false)} />
      )}
    </>
  );
}

interface FeedbackModalProps {
  onClose: () => void;
  onSubmitted: () => void;
}

function FeedbackModal({ onClose, onSubmitted }: FeedbackModalProps) {
  const { t } = useTranslation();
  const location = useLocation();
  const submit = useSubmitFeedback();
  const [severity, setSeverity] = useState<Severity>("friction");
  const [description, setDescription] = useState("");
  const [trying, setTrying] = useState("");

  const submittable = description.trim().length >= 20 && !submit.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!submittable) return;
    const sessionIdRaw = sessionStorage.getItem("mp20_session_id") || "";
    submit.mutate(
      {
        severity,
        description: description.trim(),
        what_were_you_trying: trying.trim() || undefined,
        route: location.pathname,
        session_id: sessionIdRaw,
      },
      {
        onSuccess: () => {
          toastSuccess(
            t("chrome.feedback.submit_success_title"),
            t("chrome.feedback.submit_success_body"),
          );
          onSubmitted();
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("chrome.feedback.submit_error"));
          toastError(t("chrome.feedback.submit_error"), {
            description: e.message,
          });
        },
      },
    );
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("chrome.feedback.modal_label")}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
    >
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-md flex-col gap-3 rounded-md border border-hairline-2 bg-paper p-4 shadow-lg"
      >
        <header className="flex items-baseline justify-between">
          <h2 className="font-serif text-[14px] font-medium text-ink">
            {t("chrome.feedback.title")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[12px] text-muted hover:text-ink"
            aria-label={t("chrome.feedback.close_label")}
          >
            ×
          </button>
        </header>
        <p className="font-sans text-[11px] text-muted">
          {t("chrome.feedback.context_note")}
        </p>

        <fieldset className="flex flex-col gap-1">
          <legend className="font-sans text-[10px] uppercase tracking-wider text-muted">
            {t("chrome.feedback.severity_label")}
          </legend>
          <div className="flex gap-2">
            {(["blocking", "friction", "suggestion"] as const).map((s) => (
              <label
                key={s}
                className="flex cursor-pointer items-center gap-1 rounded-sm border border-hairline-2 bg-paper-2 px-2 py-1 has-[:checked]:border-accent has-[:checked]:bg-accent/5"
              >
                <input
                  type="radio"
                  name="severity"
                  value={s}
                  checked={severity === s}
                  onChange={() => setSeverity(s)}
                />
                <span className="font-sans text-[11px] text-ink">
                  {t(`chrome.feedback.severity_${s}` as const)}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="flex flex-col gap-1">
          <span className="font-sans text-[10px] uppercase tracking-wider text-muted">
            {t("chrome.feedback.description_label")}{" "}
            <span className="text-danger">*</span>
          </span>
          <textarea
            required
            minLength={20}
            maxLength={5000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("chrome.feedback.description_placeholder")}
            className="min-h-[100px] rounded-sm border border-hairline-2 bg-paper px-2 py-1 font-sans text-[12px] text-ink focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <span className="font-sans text-[9px] text-muted">
            {t("chrome.feedback.description_hint")}
          </span>
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-sans text-[10px] uppercase tracking-wider text-muted">
            {t("chrome.feedback.trying_label")}
          </span>
          <textarea
            value={trying}
            onChange={(e) => setTrying(e.target.value)}
            placeholder={t("chrome.feedback.trying_placeholder")}
            className="min-h-[60px] rounded-sm border border-hairline-2 bg-paper px-2 py-1 font-sans text-[12px] text-ink focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            maxLength={2000}
          />
        </label>

        <footer className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            {t("chrome.feedback.cancel")}
          </Button>
          <Button
            type="submit"
            variant="default"
            disabled={!submittable}
          >
            {submit.isPending
              ? t("chrome.feedback.submit_pending")
              : t("chrome.feedback.submit")}
          </Button>
        </footer>
      </form>
    </div>
  );
}
