/**
 * Pilot disclaimer banner (Phase 5b.1, locked 2026-05-02).
 *
 * Renders a thin top banner reminding the advisor that this build is
 * a limited-beta pilot operating on real client data, with a dismiss
 * button that calls POST /api/disclaimer/acknowledge/. Dismissal is
 * server-side audit-tracked + version-aware: if DISCLAIMER_VERSION
 * is bumped, advisors see the banner again on next login until they
 * re-acknowledge, and the audit log captures every version each
 * advisor saw.
 *
 * Compliance posture: a query against
 *   AuditEvent.objects.filter(action="disclaimer_acknowledged",
 *                             metadata__advisor_id=<X>)
 * yields the full version-by-version history for advisor X.
 */
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import {
  DISCLAIMER_VERSION,
  type SessionUser,
  useAcknowledgeDisclaimer,
} from "../lib/auth";
import { normalizeApiError } from "../lib/api-error";
import { toastError } from "../lib/toast";

interface PilotBannerProps {
  user: SessionUser;
}

export function PilotBanner({ user }: PilotBannerProps) {
  const { t } = useTranslation();
  const ack = useAcknowledgeDisclaimer();

  const acknowledgedVersion = user.disclaimer_acknowledged_version || "";
  const upToDate =
    !!user.disclaimer_acknowledged_at &&
    acknowledgedVersion === DISCLAIMER_VERSION;

  if (upToDate) return null;

  const handleAcknowledge = () => {
    ack.mutate(
      { version: DISCLAIMER_VERSION },
      {
        onError: (err) => {
          const e = normalizeApiError(err, t("chrome.pilot_banner.error"));
          toastError(t("chrome.pilot_banner.error"), { description: e.message });
        },
      },
    );
  };

  return (
    <div
      role="region"
      aria-label={t("chrome.pilot_banner.aria_label")}
      className="flex items-center justify-between gap-3 border-b border-accent/30 bg-accent/10 px-4 py-2"
    >
      <p className="font-sans text-[11px] text-ink">
        <span className="mr-1 font-medium">
          {t("chrome.pilot_banner.title")}
        </span>
        {t("chrome.pilot_banner.body")}
      </p>
      <Button
        variant="outline"
        size="sm"
        onClick={handleAcknowledge}
        disabled={ack.isPending}
      >
        {ack.isPending
          ? t("chrome.pilot_banner.dismiss_pending")
          : t("chrome.pilot_banner.dismiss")}
      </Button>
    </div>
  );
}
