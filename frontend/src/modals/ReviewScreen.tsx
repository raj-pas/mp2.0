/**
 * Review screen — full-page review of a single workspace.
 *
 * Left rail: the workspace's processing/extracted documents +
 * conflict cards + readiness checklist.
 * Right rail: per-section approval cards driven by the
 * `state.readiness` contract; commit gate at the bottom.
 *
 * Live polling on the workspace detail (locked decision #18 — 3s
 * interval while any ProcessingJob is queued/running). The state
 * endpoint is fetched eagerly so the right rail reflects the
 * latest approved-state snapshot.
 *
 * Conflict resolution UX (canon §11.4 source-priority hierarchy):
 *   - Cross-class mismatches resolve silently to the higher-priority
 *     source; they DON'T appear in the conflict cards
 *   - Same-class disagreements surface here with source attribution
 *     chips (e.g. "From KYC form (page 2)")
 *   - Advisor picks the canonical value or types an override; the
 *     PATCH /state/ call captures rationale + source_fact_ids.
 *
 * R7 v1 ships the surface for processing + readiness + section
 * approval + commit. Inline conflict-resolution cards (with
 * candidate values + source chips + resolve button) are wired
 * to the state-PATCH endpoint via `useStatePatch`; the visual
 * card layout is a focused first-cut, with R10 polish layering in
 * evidence quote tooltips and per-conflict reason capture.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { useRememberedClientId } from "../chrome/ClientPicker";
import {
  type ReviewConflict,
  type ReviewWorkspace,
  type SectionApprovalStatus,
  type WorkerHealth,
  useApproveSection,
  useCommitWorkspace,
  useUncommitWorkspace,
  useMarkManualEntry,
  useReviewWorkspace,
  useReviewedState,
  useRetryDocument,
} from "../lib/review";
import { ConflictPanel } from "./ConflictPanel";
import { DocDetailPanel } from "./DocDetailPanel";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";

interface ReviewScreenProps {
  workspaceId: string;
}

export function ReviewScreen({ workspaceId }: ReviewScreenProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [, setRememberedId] = useRememberedClientId();
  const [openDocId, setOpenDocId] = useState<number | null>(null);

  const workspaceQuery = useReviewWorkspace(workspaceId, { polling: true });
  const stateQuery = useReviewedState(workspaceId);
  const approve = useApproveSection(workspaceId);
  const commit = useCommitWorkspace(workspaceId);
  const uncommit = useUncommitWorkspace(workspaceId);
  const retry = useRetryDocument(workspaceId);
  const manualEntry = useMarkManualEntry(workspaceId);

  if (workspaceQuery.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }
  if (workspaceQuery.isError || workspaceQuery.data === undefined) {
    return (
      <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
        {t("review.load_error")}
      </p>
    );
  }

  const workspace = workspaceQuery.data;

  // Drive the commit gate off the server-provided required-sections
  // list so the frontend never drifts from `ENGINE_REQUIRED_SECTIONS`.
  // Tolerate older builds that don't yet send the field by falling back
  // to an empty list (commit will still fail server-side, just without
  // the helpful disabled hint).
  const requiredSections = workspace.required_sections ?? [];
  const approvalsByName = new Map(
    workspace.section_approvals.map((approval) => [approval.section, approval.status]),
  );
  const missingApprovals = requiredSections.filter(
    (section) => approvalsByName.get(section) !== "approved",
  );
  const allRequiredApproved = missingApprovals.length === 0;
  const engineReady = workspace.readiness?.engine_ready ?? false;
  const constructionReady = workspace.readiness?.construction_ready ?? false;
  const commitDisabled =
    !engineReady || !constructionReady || !allRequiredApproved || commit.isPending;

  function handleCommit() {
    commit.mutate(
      {},
      {
        onSuccess: (response) => {
          setRememberedId(response.household_id);
          toastSuccess(t("review.commit_success_title"), t("review.commit_success_body"));
          navigate("/");
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("review.commit_error"));
          // The commit endpoint returns a structured body for gate
          // failures: `{ code, missing_approvals, readiness, ... }`.
          // Convert that into an actionable toast so the advisor knows
          // exactly which gate to fix instead of a generic "could not
          // commit household." line.
          let description = e.message;
          if (e.code === "sections_not_approved") {
            const missing = (e.body?.missing_approvals as string[] | undefined) ?? [];
            description = t("review.commit_blocked_sections", {
              sections: missing.join(", "),
            });
          } else if (e.code === "engine_not_ready") {
            description = t("review.commit_blocked_engine");
          } else if (e.code === "construction_not_ready") {
            description = t("review.commit_blocked_construction");
          }
          toastError(t("review.commit_error"), { description });
        },
      },
    );
  }

  return (
    <section
      aria-labelledby="review-screen-title"
      className="flex flex-col gap-4 border border-hairline-2 bg-paper p-6 shadow-sm"
    >
      <header className="flex items-baseline justify-between">
        <div>
          <h2
            id="review-screen-title"
            className="font-serif text-xl font-medium tracking-tight text-ink"
          >
            {workspace.label}
          </h2>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("review.subtitle", {
              status: workspace.status,
              origin: workspace.data_origin,
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex flex-col items-end gap-1">
            {workspace.status === "committed" ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  uncommit.mutate(undefined, {
                    onSuccess: () => {
                      toastSuccess(
                        t("review.uncommit_success_title"),
                        t("review.uncommit_success_body"),
                      );
                    },
                    onError: (err) => {
                      const e = normalizeApiError(err, t("review.uncommit_error"));
                      toastError(t("review.uncommit_error"), { description: e.message });
                    },
                  });
                }}
                disabled={uncommit.isPending}
              >
                {uncommit.isPending ? t("review.uncommitting") : t("review.uncommit")}
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                onClick={handleCommit}
                disabled={commitDisabled}
              >
                {commit.isPending ? t("review.committing") : t("review.commit")}
              </Button>
            )}
            {workspace.status !== "committed" && (!commitDisabled || commit.isPending ? null : (
              <p className="font-mono text-[9px] uppercase tracking-widest text-muted">
                {!engineReady
                  ? t("review.commit_blocked_engine")
                  : !constructionReady
                    ? t("review.commit_blocked_construction")
                    : t("review.commit_blocked_sections", {
                        sections: missingApprovals.join(", "),
                      })}
              </p>
            ))}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-[1fr_360px] gap-4">
        <main className="flex flex-col gap-4">
          <WorkerHealthBanner health={workspace.worker_health} />
          <ProcessingPanel
            workspace={workspace}
            onRetry={(documentId) => retry.mutate({ documentId })}
            onMarkManualEntry={(documentId) =>
              manualEntry.mutate(
                { documentId },
                {
                  onSuccess: (response) => {
                    toastSuccess(
                      t("review.manual_entry_success_title"),
                      t("review.manual_entry_success_body", {
                        previous_code: response.previous_failure_code || "n/a",
                      }),
                    );
                  },
                  onError: (err) => {
                    const e = normalizeApiError(err, t("review.manual_entry_error"));
                    toastError(t("review.manual_entry_error"), { description: e.message });
                  },
                },
              )
            }
            onOpenDetail={(documentId) => setOpenDocId(documentId)}
            retrying={retry.isPending}
            markingManualEntry={manualEntry.isPending}
          />
          <ReadinessPanel workspace={workspace} />
          <ConflictPanel
            workspaceId={workspaceId}
            conflicts={
              ((stateQuery.data?.state as { conflicts?: ReviewConflict[] })
                ?.conflicts) ?? []
            }
            loading={stateQuery.isLoading}
          />
        </main>
        <aside className="flex flex-col gap-4">
          {(workspace.readiness?.missing ?? []).length > 0 && (
            <MissingPanel missing={workspace.readiness?.missing ?? []} />
          )}
          <SectionApprovalPanel
            workspace={workspace}
            requiredSections={requiredSections}
            approving={approve.isPending}
            onApprove={(payload) =>
              approve.mutate(payload, {
                onError: (err) => {
                  const e = normalizeApiError(err, t("review.approve_error"));
                  toastError(t("review.approve_error"), { description: e.message });
                },
              })
            }
          />
          <StatePeekPanel state={stateQuery.data?.state} />
        </aside>
      </div>
      <DocDetailPanel
        workspaceId={workspaceId}
        documentId={openDocId}
        onClose={() => setOpenDocId(null)}
      />
    </section>
  );
}

function WorkerHealthBanner({ health }: { health: WorkerHealth | undefined }) {
  const { t } = useTranslation();
  if (!health) return null;
  const status = health.status;
  const activeJobs = health.active_job_count ?? 0;
  // Show only if processing is in flight AND worker is unhealthy. Idle
  // workers with no active jobs is the steady-state and not noteworthy.
  if (status !== "stale" && status !== "offline") return null;
  if (activeJobs === 0) return null;
  const i18nKey =
    status === "stale" ? "review.worker_health.stale" : "review.worker_health.offline";
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-start gap-2 rounded-md border border-danger/30 bg-danger/10 px-3 py-2"
    >
      <span aria-hidden className="text-[14px] leading-tight text-danger">
        {"!"}
      </span>
      <div>
        <p className="font-sans text-[12px] font-medium text-ink">
          {t(`${i18nKey}_title`)}
        </p>
        <p className="font-sans text-[11px] text-muted">
          {t(`${i18nKey}_body`, { count: activeJobs })}
        </p>
      </div>
    </div>
  );
}


function ProcessingPanel({
  workspace,
  onRetry,
  onMarkManualEntry,
  onOpenDetail,
  retrying,
  markingManualEntry,
}: {
  workspace: ReviewWorkspace;
  onRetry: (documentId: number) => void;
  onMarkManualEntry: (documentId: number) => void;
  onOpenDetail: (documentId: number) => void;
  retrying: boolean;
  markingManualEntry: boolean;
}) {
  const { t } = useTranslation();
  const docs = workspace.documents;
  const counts = countByStatus(docs);
  const inFlight = counts.in_flight;
  const total = docs.length;
  const completed = counts.completed;
  const etaSeconds = inFlight > 0 ? estimateEtaSeconds(inFlight) : null;
  return (
    <section className="border border-hairline-2 bg-paper-2 p-4">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("review.processing_title")}
      </h3>
      {docs.length === 0 ? (
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("review.no_documents")}
        </p>
      ) : (
        <>
          {inFlight > 0 && (
            <div
              role="status"
              aria-live="polite"
              className="mb-3 flex items-baseline justify-between border-l-4 border-accent bg-paper px-3 py-2"
            >
              <p className="font-sans text-[12px] text-ink">
                {t("review.progress_in_flight", {
                  completed,
                  total,
                  in_flight: inFlight,
                })}
              </p>
              {etaSeconds !== null && (
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
                  {t("review.progress_eta", { seconds: etaSeconds })}
                </span>
              )}
            </div>
          )}
        <ul className="flex flex-col divide-y divide-hairline">
          {docs.map((doc) => {
            const job = workspace.processing_jobs.find((j) => j.document_id === doc.id);
            const isFailed = doc.status === "failed";
            const isManualEntry = doc.status === "manual_entry";
            const failureCode = doc.failure_code ?? "";
            // Manual-entry CTA shows when the doc is failed AND the
            // failure_code is one we know retries won't recover.
            // bedrock_token_limit is now resolved by the 16384 fix, but
            // we keep it as an eligible code in case the next-tier
            // outputs hit a higher ceiling. bedrock_non_json and
            // bedrock_schema_mismatch are explicitly retry-resistant.
            const manualEntryEligible =
              isFailed &&
              ["bedrock_token_limit", "bedrock_non_json", "bedrock_schema_mismatch"].includes(
                failureCode,
              );
            const failureMessage =
              isFailed && failureCode
                ? t(`review.failure_code.${failureCode}`, {
                    defaultValue: t("review.failure_code.fallback", {
                      code: failureCode,
                    }),
                  })
                : "";
            const failureMsgId = `doc-${doc.id}-failure-msg`;
            const showRetry = doc.retry_eligible && job?.status === "failed";
            const attempts = job?.attempts ?? 0;
            const maxAttempts = job?.max_attempts ?? 0;
            const retryLabel = retrying
              ? t("review.retrying")
              : attempts > 0 && maxAttempts > 0
                ? t("review.retry_with_attempts", { attempt: attempts, max: maxAttempts })
                : t("review.retry_document");
            return (
              <li key={doc.id} className="flex flex-col gap-2 py-2">
                <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3">
                  <button
                    type="button"
                    onClick={() => onOpenDetail(doc.id)}
                    className="flex flex-col text-left transition-colors hover:bg-paper-2 focus:bg-paper-2 focus:outline-none"
                    aria-label={t("review.open_doc_detail", { name: doc.original_filename })}
                  >
                    <span className="font-sans text-[12px] text-ink underline-offset-2 hover:underline">
                      {doc.original_filename}
                    </span>
                    <span className="font-mono text-[10px] text-muted">
                      {doc.document_type ?? doc.extension} ·{" "}
                      {(doc.file_size / 1024).toFixed(1)} KB
                    </span>
                  </button>
                  <span
                    {...(failureMessage ? { title: failureMessage } : {})}
                    aria-label={
                      failureMessage
                        ? t("review.failure_chip_aria", { message: failureMessage })
                        : undefined
                    }
                    className={cn(
                      "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest",
                      doc.status === "extracted" || doc.status === "reconciled"
                        ? "border-success/40 text-success"
                        : isFailed
                          ? "border-danger/40 text-danger cursor-help"
                          : isManualEntry
                            ? "border-accent-2/40 text-accent-2"
                            : "border-hairline text-muted",
                    )}
                  >
                    {doc.status}
                  </span>
                  {showRetry && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => onRetry(doc.id)}
                      disabled={retrying || markingManualEntry}
                      {...(failureMessage ? { "aria-describedby": failureMsgId } : {})}
                    >
                      {retryLabel}
                    </Button>
                  )}
                  {manualEntryEligible && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => onMarkManualEntry(doc.id)}
                      disabled={retrying || markingManualEntry}
                      {...(failureMessage ? { "aria-describedby": failureMsgId } : {})}
                    >
                      {t("review.mark_manual_entry")}
                    </Button>
                  )}
                </div>
                {isFailed && failureMessage && (
                  <p id={failureMsgId} className="font-mono text-[10px] text-danger">
                    {failureMessage}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
        </>
      )}
    </section>
  );
}

// Doc statuses that mean "extraction work still in flight" — see
// frontend/src/lib/review.ts DocumentStatus union for the canonical
// list. Anything not in this set is treated as terminal-ish (either
// extracted, reconciled, failed, manual_entry, unsupported, skipped).
const IN_FLIGHT_DOC_STATUSES = new Set<ReviewWorkspace["documents"][number]["status"]>([
  "uploaded",
  "classified",
  "text_extracted",
  "ocr_required",
  "facts_extracted",
]);

function countByStatus(docs: ReviewWorkspace["documents"]): {
  in_flight: number;
  completed: number;
} {
  let inFlight = 0;
  let completed = 0;
  for (const doc of docs) {
    if (IN_FLIGHT_DOC_STATUSES.has(doc.status)) {
      inFlight += 1;
    } else {
      completed += 1;
    }
  }
  return { in_flight: inFlight, completed };
}

// Heuristic ETA per doc, derived from sub-session #8.5 + #9 canary
// timings: text path ~8-12s/doc, vision_native_pdf path ~6-14s/doc.
// We bias toward the upper bound so the advisor's expectation is
// realistic instead of optimistic. Worker concurrency is 1 (single
// worker dyno) so total ETA = N × per-doc-seconds.
const PER_DOC_ETA_SECONDS = 15;

function estimateEtaSeconds(inFlight: number): number {
  return inFlight * PER_DOC_ETA_SECONDS;
}

function ReadinessPanel({ workspace }: { workspace: ReviewWorkspace }) {
  const { t } = useTranslation();
  return (
    <section className="border border-hairline-2 bg-paper-2 p-4">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("review.readiness_title")}
      </h3>
      <dl className="grid grid-cols-3 gap-3">
        <ReadyChip
          label={t("review.engine_ready")}
          ready={workspace.readiness?.engine_ready ?? false}
        />
        <ReadyChip
          label={t("review.construction_ready")}
          ready={workspace.readiness?.construction_ready ?? false}
        />
        <ReadyChip
          label={t("review.kyc_ready")}
          ready={workspace.readiness?.kyc_compliance_ready ?? false}
        />
      </dl>
    </section>
  );
}

function ReadyChip({ label, ready }: { label: string; ready: boolean }) {
  return (
    <div className="flex flex-col">
      <dt className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</dt>
      <dd
        className={cn(
          "font-mono text-[12px] uppercase tracking-widest",
          ready ? "text-success" : "text-danger",
        )}
      >
        {ready ? "✓" : "—"}
      </dd>
    </div>
  );
}

function MissingPanel({ missing }: { missing: { section: string; label: string }[] }) {
  const { t } = useTranslation();
  return (
    <section className="border border-danger/40 bg-paper-2 p-4">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-danger">
        {t("review.missing_title")}
      </h3>
      <ul className="flex flex-col gap-1">
        {missing.map((row, idx) => (
          <li
            key={`${row.section}-${idx}`}
            className="flex items-baseline justify-between font-mono text-[10px]"
          >
            <span className="text-muted">{row.section}</span>
            <span className="text-ink">{row.label}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SectionApprovalPanel({
  workspace,
  requiredSections,
  approving,
  onApprove,
}: {
  workspace: ReviewWorkspace;
  requiredSections: string[];
  approving: boolean;
  onApprove: (payload: {
    section: string;
    status: SectionApprovalStatus;
    notes?: string;
    data?: Record<string, unknown>;
  }) => void;
}) {
  const { t } = useTranslation();
  // Render the server-provided required-sections list. If the workspace
  // surfaces approvals for non-required sections (legacy data), include
  // those too so the advisor can still review them.
  const extraApprovals = workspace.section_approvals
    .map((a) => a.section)
    .filter((section) => !requiredSections.includes(section));
  const sections = [...requiredSections, ...extraApprovals];
  const approvalsByName = new Map(
    workspace.section_approvals.map((approval) => [approval.section, approval]),
  );
  return (
    <section className="border border-hairline-2 bg-paper-2 p-4">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("review.section_approval_title")}
      </h3>
      <ul className="flex flex-col divide-y divide-hairline">
        {sections.map((section) => {
          const approval = approvalsByName.get(section);
          const approved = approval?.status === "approved";
          return (
            <li key={section} className="flex items-center justify-between gap-2 py-2">
              <span className="flex flex-col">
                <span className="font-sans text-[12px] text-ink">{section}</span>
                {approval !== undefined && (
                  <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
                    {approval.status}
                  </span>
                )}
              </span>
              <Button
                type="button"
                variant={approved ? "outline" : "default"}
                size="sm"
                onClick={() =>
                  onApprove({
                    section,
                    status: "approved",
                  })
                }
                disabled={approving || approved}
                aria-label={t("review.approve_section_action", { section })}
              >
                {approved ? t("review.approved") : t("review.approve_section")}
              </Button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function StatePeekPanel({ state }: { state: Record<string, unknown> | undefined }) {
  const { t } = useTranslation();
  if (state === undefined) return null;

  // Phase 10.4: replace the raw JSON dump with a structured "About to
  // commit" summary. The advisor sees per-section counts (people /
  // accounts / goals / risk) so the commit moment is intelligible
  // without reading nested JSON. Falls back to the JSON view inside a
  // <details> for the technical case where the advisor wants the raw
  // shape.
  const summary = summarizeReviewedState(state);
  return (
    <section className="border border-hairline-2 bg-paper-2 p-4">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("review.state_peek_title")}
      </h3>
      <dl className="grid grid-cols-2 gap-3 font-sans text-[12px]">
        <CommitPreviewRow label={t("review.commit_preview.people")} value={summary.people_count} />
        <CommitPreviewRow
          label={t("review.commit_preview.accounts")}
          value={summary.accounts_count}
        />
        <CommitPreviewRow label={t("review.commit_preview.goals")} value={summary.goals_count} />
        <CommitPreviewRow
          label={t("review.commit_preview.goal_account_links")}
          value={summary.goal_account_links_count}
        />
        <CommitPreviewRow
          label={t("review.commit_preview.risk")}
          value={summary.risk_household_score ?? t("review.commit_preview.unset")}
        />
        <CommitPreviewRow
          label={t("review.commit_preview.household")}
          value={summary.household_label || t("review.commit_preview.unset")}
        />
      </dl>
      <details className="mt-3">
        <summary className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("review.commit_preview.show_raw")}
        </summary>
        <pre className="mt-2 max-h-48 overflow-auto bg-paper p-2 font-mono text-[10px] text-ink-2">
          {JSON.stringify(state, null, 2).slice(0, 1200)}
        </pre>
      </details>
    </section>
  );
}

function CommitPreviewRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-baseline justify-between border-b border-hairline pb-1">
      <dt className="font-mono text-[10px] uppercase tracking-widest text-muted">{label}</dt>
      <dd className="font-sans text-[14px] text-ink">{value}</dd>
    </div>
  );
}

function summarizeReviewedState(state: Record<string, unknown>): {
  people_count: number;
  accounts_count: number;
  goals_count: number;
  goal_account_links_count: number;
  risk_household_score: number | null;
  household_label: string;
} {
  const people = Array.isArray(state.people) ? state.people : [];
  const accounts = Array.isArray(state.accounts) ? state.accounts : [];
  const goals = Array.isArray(state.goals) ? state.goals : [];
  const goalAccountLinks = Array.isArray(state.goal_account_links)
    ? state.goal_account_links
    : [];
  const risk = isObjectLike(state.risk) ? state.risk : null;
  const household = isObjectLike(state.household) ? state.household : null;

  const householdScoreRaw = risk?.household_score;
  const householdScore =
    typeof householdScoreRaw === "number" ? householdScoreRaw : null;
  const householdLabelRaw = household?.display_name;
  const householdLabel =
    typeof householdLabelRaw === "string" ? householdLabelRaw : "";

  return {
    people_count: people.length,
    accounts_count: accounts.length,
    goals_count: goals.length,
    goal_account_links_count: goalAccountLinks.length,
    risk_household_score: householdScore,
    household_label: householdLabel,
  };
}

function isObjectLike(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
