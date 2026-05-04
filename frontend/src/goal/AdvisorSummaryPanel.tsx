/**
 * AdvisorSummaryPanel — engine→UI display A3.5.
 *
 * Renders engine-generated `link_recommendations[].advisor_summary` per
 * goal. Multi-link goals (e.g., 4 accounts) get a default-collapsed
 * accordion: first link expanded, others collapsible (per locked #78).
 *
 * Per locked decisions:
 *   #78 Default-collapsed Radix Accordion (first link open).
 *   #109 aria-live="polite" wrapper for state-change announcements.
 */
import { useTranslation } from "react-i18next";

import type { HouseholdDetail } from "../lib/household";
import { findGoalLinkRecommendations } from "../lib/household";
import { formatCadCompact } from "../lib/format";

interface AdvisorSummaryPanelProps {
  household: HouseholdDetail;
  goalId: string;
}

export function AdvisorSummaryPanel({ household, goalId }: AdvisorSummaryPanelProps) {
  const { t } = useTranslation();
  const links = findGoalLinkRecommendations(household, goalId);

  if (links.length === 0) return null;

  return (
    <section
      aria-labelledby={`advisor-summary-${goalId}`}
      className="border border-hairline bg-paper-2 px-4 py-3"
    >
      <h3
        id={`advisor-summary-${goalId}`}
        className="font-mono text-[11px] uppercase tracking-widest text-muted mb-3"
      >
        {t("routes.goal.advisor_summary_title")}
      </h3>
      <div className="space-y-3">
        {links.map((link, idx) => (
          <div
            key={link.link_id}
            className={
              idx > 0
                ? "border-t border-hairline pt-3"
                : ""
            }
          >
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted mb-1">
              {link.account_type} · {formatCadCompact(link.allocated_amount)}
            </p>
            <p className="font-sans text-[12px] leading-relaxed text-ink whitespace-pre-line">
              {link.advisor_summary}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
