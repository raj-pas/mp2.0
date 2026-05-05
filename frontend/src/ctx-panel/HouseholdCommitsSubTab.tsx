/**
 * HouseholdCommitsSubTab — plan v20 §A1.36 (P9/P2.3 + G10).
 *
 * Renders the chronological advisor-relevant audit-event feed for the
 * currently-selected household. Sourced from the new household-scoped
 * `/api/clients/<id>/audit-events/?kind=commits` endpoint.
 *
 * UX:
 *   - Newest first (matches AuditEvent.Meta.ordering on the backend).
 *   - One row per event: action label + actor + timestamp.
 *   - Visual badge distinguishes the FIRST `review_state_committed`
 *     event (initial commit) from subsequent re-opens / re-commits.
 *   - Forward-compat: surfaces `entities_reconciled_via_button`
 *     (P2.5), `account_assigned_to_goals` (P13), `fact_override_applied`
 *     etc — those events land later but the rendering primitive is
 *     ready.
 *   - Empty state per §A1.54: graceful copy when 0 events.
 *   - Pagination: 50 per page (Show more button advances page).
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { useRememberedClientId } from "../chrome/ClientPicker";
import { type AuditEventRow, useAuditEventsForHousehold } from "../lib/clients";

const COMMIT_ACTIONS = new Set([
  "review_state_committed",
  "review_workspace_uncommitted",
  "review_workspace_reopened",
]);

export function HouseholdCommitsSubTab() {
  const { t } = useTranslation();
  const [rememberedId] = useRememberedClientId();
  const [page, setPage] = useState(1);
  const query = useAuditEventsForHousehold(rememberedId, "commits", page);

  if (rememberedId === null) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("routes.household.select_first")}
      </p>
    );
  }
  if (query.isPending) return <Skeleton className="h-32 w-full" />;
  if (query.isError) {
    return (
      <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
        {t("errors.preview_failed")}
      </p>
    );
  }
  const events = query.data?.events ?? [];
  const total = query.data?.total ?? 0;
  if (events.length === 0) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("ctx.history.commits_empty")}
      </p>
    );
  }

  // Determine which rows are "initial commit" vs "re-open" — the
  // chronologically FIRST `review_state_committed` row across the
  // full feed is the initial commit; later commits are re-opens.
  // We approximate per-page by counting commits in the visible page.
  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col divide-y divide-hairline">
        {events.map((event, idx) => (
          <CommitEventRow
            key={event.id}
            event={event}
            // Index in the visible page; the LAST commit row in the
            // newest-first ordering (i.e. higher idx) is older / initial.
            isInitialCommit={
              event.action === "review_state_committed" &&
              idx === lastCommitIndex(events)
            }
          />
        ))}
      </ul>
      {events.length < total && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setPage((p) => p + 1)}
        >
          {t("ctx.history.commits_show_more", { remaining: total - events.length })}
        </Button>
      )}
    </div>
  );
}

function lastCommitIndex(events: AuditEventRow[]): number {
  let idx = -1;
  events.forEach((e, i) => {
    if (e.action === "review_state_committed") idx = i;
  });
  return idx;
}

function CommitEventRow({
  event,
  isInitialCommit,
}: {
  event: AuditEventRow;
  isInitialCommit: boolean;
}) {
  const { t } = useTranslation();
  const actionLabel = useMemo(() => formatActionLabel(event.action, t), [event.action, t]);
  const timestamp = event.created_at ? new Date(event.created_at).toLocaleString() : "—";
  const isCommit = COMMIT_ACTIONS.has(event.action);
  return (
    <li className="flex flex-col gap-1 py-2">
      <div className="flex items-baseline justify-between">
        <span className="font-sans text-[12px] font-medium text-ink">{actionLabel}</span>
        {isCommit && (
          <span
            data-testid="commit-badge"
            className={`font-mono text-[9px] uppercase tracking-widest ${
              isInitialCommit ? "text-accent-2" : "text-ink"
            }`}
          >
            {isInitialCommit
              ? t("ctx.history.badge_initial_commit")
              : t("ctx.history.badge_re_open")}
          </span>
        )}
      </div>
      <div className="flex items-baseline justify-between font-mono text-[10px]">
        <span className="text-muted">
          {event.actor} · {timestamp}
        </span>
        <WorkspaceLink event={event} />
      </div>
    </li>
  );
}

function WorkspaceLink({ event }: { event: AuditEventRow }) {
  const { t } = useTranslation();
  const workspaceId =
    event.entity_type === "review_workspace" && typeof event.entity_id === "string"
      ? event.entity_id
      : null;
  if (!workspaceId) return null;
  return (
    <a
      href={`/review/${encodeURIComponent(workspaceId)}`}
      className="text-accent-2 underline hover:text-ink"
    >
      {t("ctx.history.workspace_link")}
    </a>
  );
}

function formatActionLabel(action: string, t: (k: string) => string): string {
  const i18nKey = `ctx.history.action.${action}`;
  const translated = t(i18nKey);
  // Identity i18n in tests returns the key — fall back to the action
  // string when no translation is registered.
  if (translated === i18nKey) return action.replace(/_/g, " ");
  return translated;
}
