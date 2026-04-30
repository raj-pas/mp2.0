/**
 * ReviewRoute — landing surface at `/review` (canon §6.7,
 * locked decision #7 primary onboarding path).
 *
 * Layout:
 *   - DocDropOverlay (always visible) — start a new workspace
 *   - Review queue — workspaces in flight (left side)
 *   - ReviewScreen (right side) — selected workspace's processing +
 *     readiness + section-approval + commit gate
 *
 * Selected-workspace state is held in the route component so a
 * fresh-uploaded workspace flows directly into the review screen
 * without an extra click.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { DocDropOverlay } from "../modals/DocDropOverlay";
import { ReviewScreen } from "../modals/ReviewScreen";
import { useReviewWorkspaces } from "../lib/review";
import { cn } from "../lib/cn";

export function ReviewRoute() {
  const { t } = useTranslation();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const workspaces = useReviewWorkspaces();

  return (
    <main className="flex flex-1 flex-col gap-4 overflow-y-auto bg-paper p-6">
      <header>
        <h1 className="font-serif text-2xl font-medium tracking-tight text-ink">
          {t("review_route.title")}
        </h1>
        <p className="mt-1 text-[12px] text-muted">{t("review_route.subtitle")}</p>
      </header>

      <DocDropOverlay onWorkspaceReady={(id) => setSelectedWorkspaceId(id)} />

      <div className="grid grid-cols-[280px_1fr] gap-4">
        <aside
          className="flex max-h-[600px] flex-col overflow-y-auto border border-hairline-2 bg-paper p-4"
          aria-label={t("review_route.queue_title")}
        >
          <h2 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("review_route.queue_title")}
          </h2>
          {workspaces.isPending && <Skeleton className="h-32 w-full" />}
          {workspaces.isError && (
            <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
              {t("review_route.queue_error")}
            </p>
          )}
          {workspaces.isSuccess && workspaces.data.length === 0 && (
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("review_route.queue_empty")}
            </p>
          )}
          {workspaces.isSuccess && workspaces.data.length > 0 && (
            <ul className="flex flex-col divide-y divide-hairline">
              {workspaces.data.map((workspace) => {
                const active = workspace.external_id === selectedWorkspaceId;
                return (
                  <li key={workspace.external_id}>
                    <button
                      type="button"
                      onClick={() => setSelectedWorkspaceId(workspace.external_id)}
                      className={cn(
                        "flex w-full flex-col gap-0.5 px-2 py-2 text-left transition-colors",
                        active ? "bg-paper-2" : "hover:bg-paper-2",
                      )}
                    >
                      <span className="font-sans text-[12px] font-medium text-ink">
                        {workspace.label}
                      </span>
                      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
                        {t("review_route.queue_row_meta", {
                          status: workspace.status,
                          origin: workspace.data_origin,
                          count: workspace.document_count,
                        })}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>

        <section className="flex-1">
          {selectedWorkspaceId === null ? (
            <div className="flex h-full items-center justify-center border border-hairline-2 bg-paper-2 p-12">
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
                {t("review_route.select_prompt")}
              </p>
            </div>
          ) : (
            <ReviewScreen workspaceId={selectedWorkspaceId} />
          )}
        </section>
      </div>
    </main>
  );
}
