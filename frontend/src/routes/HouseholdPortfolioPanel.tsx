/**
 * HouseholdPortfolioPanel — engine→UI display A4 + post-tag A4 stale/integrity.
 *
 * Renders the engine's household-level rollup (expected return + volatility
 * + top funds breakdown) between AUM strip and treemap on HouseholdRoute.
 *
 * Mirrors RecommendationBanner failure pattern (locked #19) AND stale-state
 * pattern (post-tag locked §3.2):
 *   - run present + status=current        → metrics + top 4 funds
 *   - run present + status ∈ {invalidated, superseded, declined}
 *                                          → muted metrics + warning chip + Regenerate
 *   - run present + status=hash_mismatch   → muted metrics + danger chip (NO Regenerate)
 *   - rollup null + failure                → inline error + Retry + toast (locked #9)
 *   - rollup null + no failure (cold)      → Generate CTA + readiness blockers
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import type { HouseholdDetail, PortfolioGenerationBlocker } from "../lib/household";
import { findHouseholdRollup } from "../lib/household";
import { formatPct } from "../lib/format";
import { useGeneratePortfolio } from "../lib/preview";
import { toastError } from "../lib/toast";

interface HouseholdPortfolioPanelProps {
  household: HouseholdDetail;
}

export function HouseholdPortfolioPanel({ household }: HouseholdPortfolioPanelProps) {
  const { t } = useTranslation();
  const generate = useGeneratePortfolio(household.id);
  const rollup = findHouseholdRollup(household);
  const failure = household.latest_portfolio_failure;

  // Surface failure via toast on mount (per locked #9 + #109)
  const lastSurfacedRef = useRef<string | null>(null);
  useEffect(() => {
    if (failure && failure.occurred_at !== lastSurfacedRef.current) {
      toastError(t("routes.household.generation_failed_title"), {
        description: t("routes.household.generation_failed_body", {
          reason: failure.reason_code,
        }),
      });
      lastSurfacedRef.current = failure.occurred_at;
    }
  }, [failure, t]);

  // No run + recent failure → inline error
  if (rollup === null && failure !== null) {
    return (
      <section
        role="status"
        aria-live="polite"
        aria-labelledby={`household-portfolio-${household.id}`}
        className="border border-danger bg-paper-2 px-4 py-3 my-3"
      >
        <div className="flex items-center justify-between gap-3">
          <h3
            id={`household-portfolio-${household.id}`}
            className="font-mono text-[11px] uppercase tracking-widest text-danger"
          >
            {t("routes.household.portfolio_panel_title")} —{" "}
            {t("routes.household.generation_failed_inline", { reason: failure.reason_code })}
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
          >
            {generate.isPending ? t("routes.household.regenerating") : t("routes.household.retry")}
          </Button>
        </div>
      </section>
    );
  }

  // No run + no failure (cold start) → Generate CTA. If the household has
  // outstanding readiness blockers (account under-allocated, missing
  // holdings, unsupported account type, etc.), surface them inline so the
  // advisor sees what to fix BEFORE clicking Generate. Per locked #9 the
  // typed-skip path is silent, so without this list there's no persistent
  // signal of what's blocking generation.
  //
  // Structured blockers (plan v20 §A1.27) are preferred when present:
  // each carries a `code` + `ui_action` enabling per-blocker fix CTAs.
  // Falls back to humanized strings (`readiness_blockers`) when the new
  // field is null/empty (older payloads + §3.16 backwards-compat).
  if (rollup === null) {
    const structured = household.structured_readiness_blockers ?? null;
    const humanized = household.readiness_blockers ?? [];
    const hasStructured = structured !== null && structured.length > 0;
    const hasAnyBlockers = hasStructured || humanized.length > 0;
    return (
      <section
        role="status"
        aria-live="polite"
        aria-labelledby={`household-portfolio-${household.id}`}
        className="border border-hairline bg-paper-2 px-4 py-3 my-3 relative z-10"
      >
        <div className="flex items-center justify-between gap-3">
          <h3
            id={`household-portfolio-${household.id}`}
            className="font-mono text-[11px] uppercase tracking-widest text-muted"
          >
            {t("routes.household.portfolio_panel_title")} —{" "}
            {t("routes.household.portfolio_no_run")}
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => generate.mutate()}
            disabled={generate.isPending || hasAnyBlockers}
          >
            {generate.isPending
              ? t("routes.household.regenerating")
              : t("routes.household.generate")}
          </Button>
        </div>
        {hasStructured && structured !== null ? (
          <StructuredBlockerBanner blockers={structured} />
        ) : humanized.length > 0 ? (
          <div className="mt-3 border-t border-hairline pt-3">
            <p className="font-mono text-[10px] uppercase tracking-widest text-warning mb-2">
              {t("routes.household.readiness_blockers_title")}
            </p>
            <ul className="space-y-1 list-disc list-inside font-sans text-[12px] text-ink">
              {humanized.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    );
  }

  // Stale / integrity chip variants (post-tag locked §3.2)
  const run = household.latest_portfolio_run;
  const status = run?.status ?? "current";
  const signature = run?.run_signature ? run.run_signature.slice(0, 8) : "";
  const isStale =
    status === "invalidated" || status === "superseded" || status === "declined";
  const isIntegrityIssue = status === "hash_mismatch";
  const isMuted = isStale || isIntegrityIssue;

  // Top 4 funds by weight
  const topFunds = [...rollup.allocations]
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 4);

  // hash_mismatch → engineering-only chip; NO Regenerate; metrics muted
  if (isIntegrityIssue) {
    return (
      <section
        role="alert"
        aria-labelledby={`household-portfolio-${household.id}`}
        className="border border-danger bg-paper-2 px-4 py-3 my-3"
      >
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h3
            id={`household-portfolio-${household.id}`}
            className="font-mono text-[11px] uppercase tracking-widest text-danger"
          >
            {t("routes.household.integrity_chip_label", { signature })}
          </h3>
        </div>
        <div className="opacity-40 pointer-events-none" aria-hidden>
          <div className="grid grid-cols-4 gap-2">
            {topFunds.map((alloc) => (
              <div key={alloc.sleeve_id} className="border-l-2 border-hairline pl-2">
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  {alloc.sleeve_name}
                </div>
                <div className="font-mono text-[12px] text-ink mt-0.5">
                  {formatPct(alloc.weight * 100)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  // invalidated / superseded / declined → stale chip + Regenerate; metrics muted
  if (isStale) {
    return (
      <section
        role="status"
        aria-live="polite"
        aria-labelledby={`household-portfolio-${household.id}`}
        className="border border-warning bg-paper-2 px-4 py-3 my-3"
      >
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h3
            id={`household-portfolio-${household.id}`}
            className="font-mono text-[11px] uppercase tracking-widest text-warning"
          >
            {t("routes.household.stale_chip_label", { signature })}
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
          >
            {generate.isPending
              ? t("routes.household.regenerating")
              : t("routes.household.regenerate")}
          </Button>
        </div>
        <div className="opacity-40 pointer-events-none" aria-hidden>
          <div className="grid grid-cols-4 gap-2">
            {topFunds.map((alloc) => (
              <div key={alloc.sleeve_id} className="border-l-2 border-hairline pl-2">
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  {alloc.sleeve_name}
                </div>
                <div className="font-mono text-[12px] text-ink mt-0.5">
                  {formatPct(alloc.weight * 100)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  // status === "current" → normal display with metrics + top funds
  return (
    <section
      role="status"
      aria-live="polite"
      aria-labelledby={`household-portfolio-${household.id}`}
      className={`border border-hairline bg-paper-2 px-4 py-3 my-3 ${isMuted ? "opacity-40 pointer-events-none" : ""}`}
    >
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h3
          id={`household-portfolio-${household.id}`}
          className="font-mono text-[11px] uppercase tracking-widest text-muted"
        >
          {t("routes.household.portfolio_panel_title")}
        </h3>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
            {t("routes.household.expected_return")}: {formatPct(rollup.expected_return * 100)}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
            {t("routes.household.volatility")}: {formatPct(rollup.volatility * 100)}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {topFunds.map((alloc) => (
          <div key={alloc.sleeve_id} className="border-l-2 border-hairline pl-2">
            <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
              {alloc.sleeve_name}
            </div>
            <div className="font-mono text-[12px] text-ink mt-0.5">
              {formatPct(alloc.weight * 100)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/**
 * StructuredBlockerBanner — renders structured PortfolioGenerationBlocker
 * objects with per-blocker fix-CTA buttons (Round 9 #11 LOCKED — no
 * advisor bypass; every blocker has a fix path).
 *
 * Z-order coord per §A1.19 §3.2: banner at z-10 sits BELOW sister's
 * StaleRunOverlay at z-20 — overlapping cases (stale run + readiness
 * blockers) prefer the stale overlay's affordance, which is correct
 * (advisor must regenerate from the latest committed household state).
 *
 * P11 ships the structured rendering + i18n; the actual ui_action
 * handlers (AssignAccountModal at P13, account-value editor, etc.) are
 * deferred to subsequent pairs. Each button currently console.logs the
 * intended action to make placeholder-vs-future wiring auditable.
 */
function StructuredBlockerBanner({
  blockers,
}: {
  blockers: PortfolioGenerationBlocker[];
}) {
  const { t } = useTranslation();
  return (
    <div className="mt-3 border-t border-hairline pt-3" data-testid="structured-blocker-banner">
      <p className="font-mono text-[10px] uppercase tracking-widest text-warning mb-2">
        {t("routes.household.readiness_blockers_title")}
      </p>
      <ul className="space-y-2 font-sans text-[12px] text-ink">
        {blockers.map((blocker, i) => {
          const i18nVars: Record<string, string> = {};
          if (blocker.account_label !== undefined) {
            i18nVars.account_label = blocker.account_label;
          }
          if (blocker.goal_label !== undefined) {
            i18nVars.goal_label = blocker.goal_label;
          }
          const message = t(`routes.portfolio.blocker.${blocker.code}`, i18nVars);
          const actionLabel = t(`routes.portfolio.ui_action.${blocker.ui_action}`);
          return (
            <li
              key={`${blocker.code}-${blocker.account_id ?? blocker.goal_id ?? i}`}
              className="flex items-center justify-between gap-3 border-l-2 border-warning pl-2"
              data-blocker-code={blocker.code}
            >
              <span className="text-ink">{message}</span>
              <button
                type="button"
                onClick={() => {
                  // P11 placeholder: real handlers wire in P12 (Unallocated
                  // Banner) + P13 (AssignAccountModal) sub-agents.
                  // eslint-disable-next-line no-console
                  console.log("blocker.ui_action", {
                    code: blocker.code,
                    ui_action: blocker.ui_action,
                    account_id: blocker.account_id,
                    goal_id: blocker.goal_id,
                  });
                }}
                className="font-mono text-[10px] uppercase tracking-wider text-warning border border-warning px-2 py-0.5 hover:bg-warning hover:text-paper-2"
                data-ui-action={blocker.ui_action}
              >
                {actionLabel}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
