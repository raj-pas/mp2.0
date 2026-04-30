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
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { useRememberedClientId } from "../chrome/ClientPicker";
import {
  type ReviewWorkspace,
  type SectionApprovalStatus,
  useApproveSection,
  useCommitWorkspace,
  useReviewWorkspace,
  useReviewedState,
  useRetryDocument,
} from "../lib/review";
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

  const workspaceQuery = useReviewWorkspace(workspaceId, { polling: true });
  const stateQuery = useReviewedState(workspaceId);
  const approve = useApproveSection(workspaceId);
  const commit = useCommitWorkspace(workspaceId);
  const retry = useRetryDocument(workspaceId);

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
          toastError(t("review.commit_error"), { description: e.message });
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
          <Button
            type="button"
            size="sm"
            onClick={handleCommit}
            disabled={
              !(workspace.readiness?.engine_ready ?? false) ||
              !(workspace.readiness?.construction_ready ?? false) ||
              commit.isPending
            }
          >
            {commit.isPending ? t("review.committing") : t("review.commit")}
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-[1fr_360px] gap-4">
        <main className="flex flex-col gap-4">
          <ProcessingPanel
            workspace={workspace}
            onRetry={(documentId) => retry.mutate({ documentId })}
            retrying={retry.isPending}
          />
          <ReadinessPanel workspace={workspace} />
          {/* Conflict-resolution cards land here — the wiring is in
              `useStatePatch`; R7 v1 ships the readiness gate first. */}
        </main>
        <aside className="flex flex-col gap-4">
          {(workspace.readiness?.missing ?? []).length > 0 && (
            <MissingPanel missing={workspace.readiness?.missing ?? []} />
          )}
          <SectionApprovalPanel
            workspace={workspace}
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
    </section>
  );
}

function ProcessingPanel({
  workspace,
  onRetry,
  retrying,
}: {
  workspace: ReviewWorkspace;
  onRetry: (documentId: number) => void;
  retrying: boolean;
}) {
  const { t } = useTranslation();
  const docs = workspace.documents;
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
        <ul className="flex flex-col divide-y divide-hairline">
          {docs.map((doc) => {
            const job = workspace.processing_jobs.find((j) => j.document_id === doc.id);
            return (
              <li key={doc.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 py-2">
                <div className="flex flex-col">
                  <span className="font-sans text-[12px] text-ink">{doc.original_filename}</span>
                  <span className="font-mono text-[10px] text-muted">
                    {doc.document_type ?? doc.extension} · {(doc.file_size / 1024).toFixed(1)} KB
                  </span>
                </div>
                <span
                  className={cn(
                    "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest",
                    doc.status === "extracted"
                      ? "border-success/40 text-success"
                      : doc.status === "failed"
                        ? "border-danger/40 text-danger"
                        : "border-hairline text-muted",
                  )}
                >
                  {doc.status}
                </span>
                {doc.retry_eligible && job?.status === "failed" && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => onRetry(doc.id)}
                    disabled={retrying}
                  >
                    {t("review.retry_document")}
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
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
  approving,
  onApprove,
}: {
  workspace: ReviewWorkspace;
  approving: boolean;
  onApprove: (payload: {
    section: string;
    status: SectionApprovalStatus;
    notes?: string;
    data?: Record<string, unknown>;
  }) => void;
}) {
  const { t } = useTranslation();
  const sections: string[] = ["people", "accounts", "goals", "risk", "planning"];
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
  return (
    <section className="border border-hairline-2 bg-paper-2 p-4">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("review.state_peek_title")}
      </h3>
      <pre className="max-h-48 overflow-auto bg-paper p-2 font-mono text-[10px] text-ink-2">
        {JSON.stringify(state, null, 2).slice(0, 1200)}
      </pre>
    </section>
  );
}
