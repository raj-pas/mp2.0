/**
 * IntegrityAlertOverlay — engineering-only overlay for `hash_mismatch`
 * status (Phase A4 / locked §3.2 + §3.5).
 *
 * Fires when `latest_portfolio_run.status === "hash_mismatch"`. The
 * advisor cannot regenerate — there's no advisor-recoverable action;
 * engineering must investigate the integrity violation. Backend already
 * emits a `portfolio_run_integrity_alert` AuditEvent on serializer
 * access (rate-limited via `AuditEvent.objects.filter(...).exists()`
 * per Phase A1 commit `95dfd01`); ops-runbook §2 ("Portfolio Run
 * Integrity Alert") documents the engineering response procedure.
 *
 * Visual contract (distinct from <StaleRunOverlay/>):
 *   - NO Regenerate button (advisor-not-actionable)
 *   - Renders run signature + ops-runbook reference for engineer triage
 *   - `role="alert"` (not `alertdialog`) — no focusable elements, no
 *     interaction model
 *   - No focus-trap (nothing to focus on)
 *   - Esc does NOT dismiss
 */
import { useTranslation } from "react-i18next";

interface IntegrityAlertOverlayProps {
  runSignature?: string | null;
}

export function IntegrityAlertOverlay({ runSignature }: IntegrityAlertOverlayProps) {
  const { t } = useTranslation();
  const sigPrefix =
    runSignature !== null && runSignature !== undefined && runSignature !== ""
      ? runSignature.slice(0, 8)
      : null;

  return (
    <div
      role="alert"
      aria-labelledby="integrity-overlay-title"
      aria-describedby="integrity-overlay-body"
      className="absolute inset-0 z-10 flex items-center justify-center border-2 border-danger bg-paper-2/90"
    >
      <div className="flex flex-col items-center gap-3 p-6 max-w-md text-center">
        <p
          id="integrity-overlay-title"
          className="font-mono text-[11px] uppercase tracking-widest text-danger"
        >
          {t("routes.goal.integrity_overlay_title")}
        </p>
        <p id="integrity-overlay-body" className="font-sans text-[12px] text-ink">
          {t("routes.goal.integrity_overlay_body")}
        </p>
        {sigPrefix !== null && (
          <p className="font-mono text-[10px] text-muted">
            {t("routes.goal.integrity_overlay_run_ref", { signature: sigPrefix })}
          </p>
        )}
      </div>
    </div>
  );
}
