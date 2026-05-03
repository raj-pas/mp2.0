/**
 * First-login welcome tour (Phase 5b.6, locked 2026-05-02 —
 * server-side ack via tour_completed_at User field).
 *
 * Shows a 3-step coachmark dialog on the advisor's first login:
 *   1. Pick a client from the topbar (highlights ClientPicker).
 *   2. Drill into account or goal via the treemap.
 *   3. Onboard new clients via /review (doc-drop).
 *
 * Both "Done" and "Skip" call POST /api/tour/complete/ so the tour
 * never re-shows on any device for this advisor. The endpoint is
 * idempotent + audit-event-emitting.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { type SessionUser, useCompleteTour } from "../lib/auth";

interface WelcomeTourProps {
  user: SessionUser;
}

export function WelcomeTour({ user }: WelcomeTourProps) {
  const { t } = useTranslation();
  const complete = useCompleteTour();
  const [step, setStep] = useState(0);
  const [closed, setClosed] = useState(false);

  if (user.tour_completed_at !== null) return null;
  if (closed) return null;

  const stepKeys = ["pick_client", "drill_treemap", "review_doc_drop"] as const;
  const totalSteps = stepKeys.length;
  const currentKey = stepKeys[step] ?? stepKeys[0];

  const handleFinish = () => {
    complete.mutate(undefined, {
      onSettled: () => setClosed(true),
    });
  };

  const handleNext = () => {
    if (step + 1 >= totalSteps) {
      handleFinish();
    } else {
      setStep(step + 1);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("chrome.welcome_tour.aria_label")}
      className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4"
    >
      <article className="flex w-full max-w-md flex-col gap-3 rounded-md border border-hairline-2 bg-paper p-5 shadow-lg">
        <header className="flex items-baseline justify-between">
          <h2 className="font-serif text-[15px] font-medium text-ink">
            {t("chrome.welcome_tour.title")}
          </h2>
          <span className="font-sans text-[10px] uppercase tracking-wider text-muted">
            {step + 1} / {totalSteps}
          </span>
        </header>
        <h3 className="font-serif text-[13px] text-ink">
          {t(`chrome.welcome_tour.step_${currentKey}_heading` as const)}
        </h3>
        <p className="font-sans text-[12px] text-muted">
          {t(`chrome.welcome_tour.step_${currentKey}_body` as const)}
        </p>
        <footer className="mt-2 flex justify-between">
          <Button variant="ghost" size="sm" onClick={handleFinish}>
            {t("chrome.welcome_tour.skip")}
          </Button>
          <Button variant="default" size="sm" onClick={handleNext}>
            {step + 1 >= totalSteps
              ? t("chrome.welcome_tour.done")
              : t("chrome.welcome_tour.next")}
          </Button>
        </footer>
      </article>
    </div>
  );
}
