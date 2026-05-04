/**
 * RecommendationBanner — engine→UI display A3.5.
 *
 * Shows the advisor 3 states:
 *   1. Run present:    "Recommendation <signature[:8]> • <relative_time>" + Regenerate button
 *   2. Run absent + recent failure: inline error + reason + Retry button + Sonner toast (locked #9)
 *   3. Run absent + no failure (cold start): "No recommendation generated yet" + Generate button
 *
 * Per locked decisions:
 *   #9  Failure surfacing: typed-skip silent + audit; unexpected toast + inline error.
 *   #16 Audit naming: response semantics rely on portfolio_run_generated being
 *       the canonical action (helper-side; surfaced via re-fetch invalidation).
 *   #74 Sync inline: response IS truth; mutation returns the new run synchronously.
 *   #109 aria-live="polite" so SR users hear state changes.
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import type { PortfolioGenerationFailure, PortfolioRun } from "../lib/household";
import { useGeneratePortfolio } from "../lib/preview";
import { toastError } from "../lib/toast";

interface RecommendationBannerProps {
  run: PortfolioRun | null;
  failure: PortfolioGenerationFailure | null;
  householdId: string;
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "just now";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "just now";
  const diffMs = Date.now() - t;
  const min = Math.floor(diffMs / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  return `${days}d ago`;
}

export function RecommendationBanner({
  run,
  failure,
  householdId,
}: RecommendationBannerProps) {
  const { t } = useTranslation();
  const generate = useGeneratePortfolio(householdId);

  // Surface failure via Sonner toast on mount (per locked #9).
  // Track via ref so toast fires once per unique occurred_at, not on every render.
  const lastSurfacedRef = useRef<string | null>(null);
  useEffect(() => {
    if (failure && failure.occurred_at !== lastSurfacedRef.current) {
      toastError(t("goal.generation_failed_title"), {
        description: t("goal.generation_failed_body", { reason: failure.reason_code }),
      });
      lastSurfacedRef.current = failure.occurred_at;
    }
  }, [failure, t]);

  // Run absent + recent failure → inline error banner + Retry CTA
  if (run === null && failure !== null) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center justify-between gap-3 border border-danger bg-paper-2 px-4 py-2"
      >
        <span className="font-mono text-[11px] uppercase tracking-widest text-danger">
          {t("goal.generation_failed_inline", {
            reason: failure.reason_code,
            when: formatRelativeTime(failure.occurred_at),
          })}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
        >
          {generate.isPending ? t("goal.regenerating") : t("goal.retry")}
        </Button>
      </div>
    );
  }

  // Run absent + no failure → first-time / cold-start state
  if (run === null) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center justify-between gap-3 border border-hairline bg-paper-2 px-4 py-2"
      >
        <span className="font-mono text-[11px] uppercase tracking-widest text-muted">
          {t("goal.no_recommendation_yet")}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
        >
          {generate.isPending ? t("goal.regenerating") : t("goal.generate")}
        </Button>
      </div>
    );
  }

  // Run present → normal banner with signature + freshness
  const signature = run.run_signature ? run.run_signature.slice(0, 8) : "";
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-between gap-3 border border-hairline bg-paper-2 px-4 py-2"
    >
      <span className="font-mono text-[11px] uppercase tracking-widest text-muted">
        {t("goal.recommendation_banner", {
          signature,
          when: formatRelativeTime(run.created_at),
        })}
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => generate.mutate()}
        disabled={generate.isPending}
      >
        {generate.isPending ? t("goal.regenerating") : t("goal.regenerate")}
      </Button>
    </div>
  );
}
