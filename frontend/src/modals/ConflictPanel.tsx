/**
 * Conflict-resolution panel (Phase 5a).
 *
 * Renders one card per same-class fact disagreement (canon §11.4).
 * Cross-class disagreements resolve silently in the backend
 * (`extraction/reconciliation.py:current_facts_by_field`) and never
 * appear here.
 *
 * Each card shows the candidate facts with source attribution
 * (filename + doc-type chip + confidence + redacted evidence quote)
 * and lets the advisor pick one, capture rationale, and acknowledge
 * the evidence. Submit calls POST /api/review-workspaces/<wsid>/
 * conflicts/resolve/ via `useResolveConflict`.
 *
 * Real-PII discipline (canon §11.8.3): evidence quotes are pre-
 * redacted on the server (`web/api/review_redaction.py`); this
 * component does no further redaction.
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { ConfidenceChip } from "../components/ConfidenceChip";
import { Skeleton } from "../components/ui/skeleton";
import {
  type BulkResolutionItem,
  type ConflictCandidate,
  type ResolveConflictPayload,
  type ReviewConflict,
  useBulkResolveConflicts,
  useResolveConflict,
} from "../lib/review";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";

interface ConflictPanelProps {
  workspaceId: string;
  conflicts: ReviewConflict[] | undefined;
  loading?: boolean;
}

export function ConflictPanel({
  workspaceId,
  conflicts,
  loading = false,
}: ConflictPanelProps) {
  const { t } = useTranslation();
  // Phase 5b.12 — `bulkSelections` maps field → chosen_fact_id. When
  // ≥2 entries are present, the bulk action bar offers a shared
  // rationale + evidence_ack form so the advisor doesn't repeat the
  // same KYC-supersedes-statement judgment for every Person 0 field.
  const [bulkSelections, setBulkSelections] = useState<Map<string, number>>(new Map());
  const [bulkRationale, setBulkRationale] = useState("");
  const [bulkEvidenceAck, setBulkEvidenceAck] = useState(false);
  const bulkResolve = useBulkResolveConflicts(workspaceId);

  function setBulkSelection(field: string, chosenFactId: number | null) {
    setBulkSelections((prev) => {
      const next = new Map(prev);
      if (chosenFactId === null) {
        next.delete(field);
      } else {
        next.set(field, chosenFactId);
      }
      return next;
    });
  }

  const bulkItems = useMemo<BulkResolutionItem[]>(
    () =>
      Array.from(bulkSelections.entries()).map(([field, chosen_fact_id]) => ({
        field,
        chosen_fact_id,
      })),
    [bulkSelections],
  );

  function handleSubmitBulk() {
    if (bulkItems.length < 2 || bulkRationale.trim().length < 4 || !bulkEvidenceAck) return;
    bulkResolve.mutate(
      {
        resolutions: bulkItems,
        rationale: bulkRationale.trim(),
        evidence_ack: bulkEvidenceAck,
      },
      {
        onSuccess: (response) => {
          toastSuccess(
            t("review.conflict.bulk_resolved_title"),
            t("review.conflict.bulk_resolved_body", { count: response.resolved_count }),
          );
          setBulkSelections(new Map());
          setBulkRationale("");
          setBulkEvidenceAck(false);
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("review.conflict.resolve_error"));
          toastError(t("review.conflict.resolve_error"), { description: e.message });
        },
      },
    );
  }

  if (loading) {
    return (
      <section className="flex flex-col gap-3 rounded-md border border-hairline-2 bg-paper p-4">
        <h2 className="font-serif text-[13px] font-medium text-ink">
          {t("review.conflict.heading")}
        </h2>
        <Skeleton className="h-20 w-full" />
      </section>
    );
  }

  const items = conflicts ?? [];

  if (items.length === 0) {
    return null;
  }

  const unresolvedCount = items.filter((c) => !c.resolved).length;

  return (
    <section
      aria-label={t("review.conflict.heading")}
      className="flex flex-col gap-3 rounded-md border border-hairline-2 bg-paper p-4"
    >
      <header className="flex items-baseline justify-between">
        <h2 className="font-serif text-[13px] font-medium text-ink">
          {t("review.conflict.heading")}
        </h2>
        <span className="text-[10px] uppercase tracking-wider text-muted">
          {t("review.conflict.summary", {
            unresolved: unresolvedCount,
            total: items.length,
          })}
        </span>
      </header>
      {bulkItems.length >= 2 && (
        <BulkResolveBar
          count={bulkItems.length}
          rationale={bulkRationale}
          onRationaleChange={setBulkRationale}
          evidenceAck={bulkEvidenceAck}
          onEvidenceAckChange={setBulkEvidenceAck}
          onSubmit={handleSubmitBulk}
          submitting={bulkResolve.isPending}
          onCancel={() => {
            setBulkSelections(new Map());
            setBulkRationale("");
            setBulkEvidenceAck(false);
          }}
        />
      )}
      <ul className="flex flex-col gap-3">
        {items.map((conflict) => (
          <li key={conflict.field}>
            <ConflictCard
              workspaceId={workspaceId}
              conflict={conflict}
              bulkSelectedFactId={bulkSelections.get(conflict.field) ?? null}
              onBulkSelect={(chosenFactId) => setBulkSelection(conflict.field, chosenFactId)}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

interface BulkResolveBarProps {
  count: number;
  rationale: string;
  onRationaleChange: (value: string) => void;
  evidenceAck: boolean;
  onEvidenceAckChange: (value: boolean) => void;
  onSubmit: () => void;
  onCancel: () => void;
  submitting: boolean;
}

function BulkResolveBar({
  count,
  rationale,
  onRationaleChange,
  evidenceAck,
  onEvidenceAckChange,
  onSubmit,
  onCancel,
  submitting,
}: BulkResolveBarProps) {
  const { t } = useTranslation();
  const submittable = !submitting && rationale.trim().length >= 4 && evidenceAck;
  return (
    <section
      aria-label={t("review.conflict.bulk_bar_aria")}
      className="flex flex-col gap-2 border border-accent/40 bg-accent/5 p-3"
    >
      <header className="flex items-baseline justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-accent">
          {t("review.conflict.bulk_bar_title", { count })}
        </h3>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={submitting}>
          {t("review.conflict.bulk_cancel")}
        </Button>
      </header>
      <p className="font-sans text-[11px] text-muted">{t("review.conflict.bulk_bar_body")}</p>
      <textarea
        value={rationale}
        onChange={(e) => onRationaleChange(e.target.value)}
        disabled={submitting}
        rows={2}
        placeholder={t("review.conflict.rationale_placeholder")}
        className="border border-hairline-2 bg-paper px-2 py-1 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
      />
      <label className="flex items-start gap-2 font-sans text-[11px] text-ink">
        <input
          type="checkbox"
          checked={evidenceAck}
          onChange={(e) => onEvidenceAckChange(e.target.checked)}
          disabled={submitting}
          className="mt-0.5"
        />
        <span>{t("review.conflict.evidence_ack")}</span>
      </label>
      <div className="flex items-center justify-end">
        <Button type="button" size="sm" onClick={onSubmit} disabled={!submittable}>
          {submitting
            ? t("review.conflict.bulk_submit_pending")
            : t("review.conflict.bulk_submit", { count })}
        </Button>
      </div>
    </section>
  );
}

interface ConflictCardProps {
  workspaceId: string;
  conflict: ReviewConflict;
  /** Phase 5b.12: panel-level bulk selection. null = not in bulk. */
  bulkSelectedFactId?: number | null;
  /** Phase 5b.12: toggles the panel-level bulk selection map. */
  onBulkSelect?: (chosenFactId: number | null) => void;
}

export function ConflictCard({
  workspaceId,
  conflict,
  bulkSelectedFactId = null,
  onBulkSelect,
}: ConflictCardProps) {
  const { t } = useTranslation();
  const resolve = useResolveConflict(workspaceId);
  const [chosenFactId, setChosenFactId] = useState<number | null>(
    conflict.chosen_fact_id ?? null,
  );
  const [rationale, setRationale] = useState<string>(conflict.rationale ?? "");
  const [evidenceAck, setEvidenceAck] = useState<boolean>(
    conflict.evidence_ack ?? false,
  );

  const candidates = conflict.candidates ?? [];
  const submittable =
    !conflict.resolved &&
    chosenFactId !== null &&
    rationale.trim().length >= 4 &&
    evidenceAck;
  const inBulk = bulkSelectedFactId !== null;

  const handleSubmit = () => {
    if (!submittable || chosenFactId === null) return;
    const payload: ResolveConflictPayload = {
      field: conflict.field,
      chosen_fact_id: chosenFactId,
      rationale: rationale.trim(),
      evidence_ack: evidenceAck,
    };
    resolve.mutate(payload, {
      onSuccess: () => {
        toastSuccess(
          t("review.conflict.resolved_toast_title"),
          t("review.conflict.resolved_toast_body", { label: conflict.label }),
        );
      },
      onError: (err) => {
        const e = normalizeApiError(err, t("review.conflict.resolve_error"));
        toastError(t("review.conflict.resolve_error"), {
          description: e.message,
        });
      },
    });
  };

  return (
    <article
      className={cn(
        "rounded-md border bg-paper-2 p-3",
        conflict.resolved
          ? "border-accent/40"
          : conflict.required
            ? "border-danger/30"
            : "border-hairline-2",
      )}
    >
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className="font-serif text-[12px] font-medium text-ink">
          {conflict.label}
        </h3>
        <div className="flex items-center gap-1">
          <span className="rounded-sm bg-ink/5 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-muted">
            {conflict.section}
          </span>
          {conflict.required && (
            <span className="rounded-sm bg-danger/10 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-danger">
              {t("review.conflict.required")}
            </span>
          )}
          {conflict.resolved && (
            <span className="rounded-sm bg-accent/15 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-accent-2">
              {t("review.conflict.resolved_state")}
            </span>
          )}
        </div>
      </header>

      {conflict.resolved ? (
        <ResolvedConflictBody conflict={conflict} />
      ) : (
        <fieldset className="flex flex-col gap-3">
          <legend className="sr-only">
            {t("review.conflict.candidates_legend", { label: conflict.label })}
          </legend>
          <ol className="flex flex-col gap-2">
            {candidates.map((candidate) => (
              <li key={candidate.fact_id}>
                <CandidateRow
                  candidate={candidate}
                  selected={chosenFactId === candidate.fact_id}
                  onSelect={() => setChosenFactId(candidate.fact_id)}
                  fieldName={`conflict-${conflict.field}`}
                />
              </li>
            ))}
          </ol>

          {onBulkSelect !== undefined && chosenFactId !== null && (
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={inBulk && bulkSelectedFactId === chosenFactId}
                onChange={(e) => {
                  onBulkSelect(e.target.checked ? chosenFactId : null);
                }}
                className="mt-0.5"
              />
              <span className="font-sans text-[11px] text-ink">
                {t("review.conflict.add_to_bulk")}
              </span>
            </label>
          )}

          {!inBulk && (
            <>
              <label className="flex flex-col gap-1">
                <span className="font-sans text-[10px] uppercase tracking-wider text-muted">
                  {t("review.conflict.rationale_label")}
                </span>
                <textarea
                  className="min-h-[60px] rounded-sm border border-hairline-2 bg-paper px-2 py-1 font-sans text-[12px] text-ink focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  placeholder={t("review.conflict.rationale_placeholder")}
                  maxLength={500}
                />
              </label>

              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={evidenceAck}
                  onChange={(e) => setEvidenceAck(e.target.checked)}
                  className="mt-0.5"
                />
                <span className="font-sans text-[11px] text-ink">
                  {t("review.conflict.evidence_ack")}
                </span>
              </label>

              <div className="flex items-center justify-end">
                <Button
                  variant="default"
                  size="sm"
                  disabled={!submittable || resolve.isPending}
                  onClick={handleSubmit}
                >
                  {resolve.isPending
                    ? t("review.conflict.submit_pending")
                    : t("review.conflict.submit")}
                </Button>
              </div>
            </>
          )}
        </fieldset>
      )}
    </article>
  );
}

interface CandidateRowProps {
  candidate: ConflictCandidate;
  selected: boolean;
  onSelect: () => void;
  fieldName: string;
}

function CandidateRow({
  candidate,
  selected,
  onSelect,
  fieldName,
}: CandidateRowProps) {
  const valueDisplay = formatCandidateValue(candidate.value);
  return (
    <label
      className={cn(
        "flex cursor-pointer flex-col gap-1.5 rounded-sm border bg-paper p-2 transition-colors",
        selected
          ? "border-accent bg-accent/5"
          : "border-hairline-2 hover:border-accent/40",
      )}
    >
      <div className="flex items-baseline gap-2">
        <input
          type="radio"
          name={fieldName}
          checked={selected}
          onChange={onSelect}
          className="mt-0.5"
        />
        <span className="flex-1 font-sans text-[12px] font-medium text-ink">
          {valueDisplay}
        </span>
        <ConfidenceChip level={candidate.confidence} />
      </div>
      <div className="ml-5 flex flex-wrap gap-1.5">
        <span className="rounded-sm bg-ink/5 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-muted">
          {candidate.source_document_type}
        </span>
        <span className="font-sans text-[9px] text-muted">
          {candidate.source_document_filename}
          {candidate.source_page ? ` · p.${candidate.source_page}` : ""}
        </span>
      </div>
      {candidate.redacted_evidence_quote ? (
        <p className="ml-5 line-clamp-2 font-sans text-[10px] italic text-muted">
          &ldquo;{candidate.redacted_evidence_quote}&rdquo;
        </p>
      ) : null}
    </label>
  );
}

function ResolvedConflictBody({ conflict }: { conflict: ReviewConflict }) {
  const { t } = useTranslation();
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-sans text-[11px]">
      <dt className="text-muted">{t("review.conflict.chosen_value_label")}</dt>
      <dd className="text-ink">{formatCandidateValue(conflict.resolution)}</dd>
      {conflict.rationale ? (
        <>
          <dt className="text-muted">
            {t("review.conflict.rationale_label")}
          </dt>
          <dd className="text-ink">{conflict.rationale}</dd>
        </>
      ) : null}
      {conflict.resolved_by ? (
        <>
          <dt className="text-muted">{t("review.conflict.resolved_by")}</dt>
          <dd className="text-ink">{conflict.resolved_by}</dd>
        </>
      ) : null}
    </dl>
  );
}

function formatCandidateValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
