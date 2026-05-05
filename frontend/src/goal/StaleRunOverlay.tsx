/**
 * StaleRunOverlay — advisor-actionable overlay for the 3 stale statuses
 * (Phase A4 / locked §3.2 + #18 + #68).
 *
 * Fires when `latest_portfolio_run.status` ∈ { invalidated, superseded,
 * declined }. The 3 status variants share the bespoke modal pattern but
 * differ in copy:
 *   - invalidated / superseded → "Recommendation is stale" / "Regenerate to refresh"
 *   - declined                 → "Run was declined" / "Regenerate to retry"
 *
 * The 4th status `hash_mismatch` routes to <IntegrityAlertOverlay/> instead
 * (engineering-only; no advisor action).
 *
 * Focus model (mirror DocDetailPanel.tsx:56-67 + locked #68):
 *   - on mount: capture `document.activeElement` → `previousFocusRef`;
 *               auto-focus the Regenerate button
 *   - on unmount: restore focus to `previousFocusRef.current`
 *   - Esc key:   does NOT dismiss (overlay is informational, not modal —
 *                advisor cannot bypass; must regenerate); blurs active
 *                element so Tab cycle doesn't trap behind the overlay
 *   - Tab key:   focus-traps to the Regenerate button (only focusable
 *                element); reduces risk of advisor reaching muted engine
 *                panels through keyboard navigation
 *
 * ARIA: `role="alertdialog"` + `aria-modal="true"` + `aria-labelledby` +
 * `aria-describedby` per WAI-ARIA Authoring Practices for modal dialogs
 * with a primary action button.
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";

export type StaleStatus = "invalidated" | "superseded" | "declined";

interface StaleRunOverlayProps {
  status: StaleStatus;
  onRegenerate: () => void;
  isPending: boolean;
}

export function StaleRunOverlay({ status, onRegenerate, isPending }: StaleRunOverlayProps) {
  const { t } = useTranslation();
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const regenerateButtonRef = useRef<HTMLButtonElement | null>(null);

  // Capture previous focus + auto-focus Regenerate on mount; restore on unmount.
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    regenerateButtonRef.current?.focus();
    return () => {
      previousFocusRef.current?.focus();
    };
  }, []);

  // Esc → does NOT dismiss (informational, not modal); blur active element so
  // Tab cycle doesn't trap behind the overlay. Tab → focus stays on the
  // Regenerate button (only focusable element inside the overlay).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        (document.activeElement as HTMLElement | null)?.blur();
        return;
      }
      if (event.key === "Tab") {
        const button = regenerateButtonRef.current;
        if (button !== null && document.activeElement !== button) {
          event.preventDefault();
          button.focus();
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const titleKey =
    status === "declined"
      ? "routes.goal.declined_overlay_title"
      : "routes.goal.stale_overlay_title";
  const bodyKey =
    status === "declined"
      ? "routes.goal.declined_overlay_body"
      : "routes.goal.stale_overlay_body";

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="stale-overlay-title"
      aria-describedby="stale-overlay-body"
      className="absolute inset-0 z-10 flex items-center justify-center border-2 border-warning bg-paper-2/90"
    >
      <div className="flex flex-col items-center gap-3 p-6 max-w-md text-center">
        <p
          id="stale-overlay-title"
          className="font-mono text-[11px] uppercase tracking-widest text-warning"
        >
          {t(titleKey)}
        </p>
        <p id="stale-overlay-body" className="font-sans text-[12px] text-ink">
          {t(bodyKey)}
        </p>
        <Button
          ref={regenerateButtonRef}
          type="button"
          variant="default"
          onClick={onRegenerate}
          disabled={isPending}
        >
          {isPending ? t("routes.goal.regenerating") : t("routes.goal.stale_overlay_regenerate")}
        </Button>
      </div>
    </div>
  );
}
