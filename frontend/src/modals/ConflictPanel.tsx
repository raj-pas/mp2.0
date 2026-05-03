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
import { Check, ChevronDown, ChevronRight, Loader2 } from "lucide-react";

import { Button } from "../components/ui/button";
import { ConfidenceChip } from "../components/ConfidenceChip";
import { Skeleton } from "../components/ui/skeleton";
import {
  type BulkResolutionItem,
  type ConflictCandidate,
  type ResolveConflictPayload,
  type ReviewConflict,
  useBulkResolveConflicts,
  useDeferConflict,
  useResolveConflict,
} from "../lib/review";
import { normalizeApiError } from "../lib/api-error";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";
import { useLocalStorage } from "../lib/local-storage";

/**
 * Tier 3 polish (production-quality-bar §1.6 + §1.10):
 *
 * - `cardState` derives a tri-state visual progression
 *   ("unresolved" / "resolving" / "resolved") from the live mutation
 *   hooks already in `lib/review.ts`. The card never holds its own
 *   "saving" state — it reads `useResolveConflict().isPending` (or, for
 *   bulk, `useBulkResolveConflicts().isPending` propagated via prop) so
 *   the visual stays in lock-step with the wire request.
 * - Active vs Resolved grouping. Within each group, items are sorted by
 *   `field` (== `field_path`) ascending so related conflicts cluster.
 *   The Resolved group is collapsible and the collapse-state is
 *   persisted via `useLocalStorage` (key `mp20.conflict-panel.resolved-collapsed`).
 *
 * Reduced-motion: the spinner uses `animate-spin` which the global
 * `prefers-reduced-motion: reduce` rule in `index.css` degrades to
 * `animation-duration: 1ms` (effectively static).
 */
type CardState = "unresolved" | "resolving" | "resolved";

const RESOLVED_COLLAPSED_STORAGE_KEY = "mp20.conflict-panel.resolved-collapsed";

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

  // Tier 3 §1.6: split into Active vs Resolved groups; sort each by
  // field path so related fields (e.g. people[0].*) cluster.
  const sorted = [...items].sort((a, b) => a.field.localeCompare(b.field));
  const activeItems = sorted.filter((c) => !c.resolved);
  const resolvedItems = sorted.filter((c) => c.resolved);

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
      {activeItems.length > 0 && (
        <ActiveGroup
          workspaceId={workspaceId}
          items={activeItems}
          bulkSelections={bulkSelections}
          onBulkSelect={setBulkSelection}
          bulkResolvePending={bulkResolve.isPending}
        />
      )}
      {resolvedItems.length > 0 && (
        <ResolvedGroup workspaceId={workspaceId} items={resolvedItems} />
      )}
    </section>
  );
}

interface ActiveGroupProps {
  workspaceId: string;
  items: ReviewConflict[];
  bulkSelections: Map<string, number>;
  onBulkSelect: (field: string, chosenFactId: number | null) => void;
  bulkResolvePending: boolean;
}

function ActiveGroup({
  workspaceId,
  items,
  bulkSelections,
  onBulkSelect,
  bulkResolvePending,
}: ActiveGroupProps) {
  const { t } = useTranslation();
  const headingId = "polish-c-conflict-active-heading";
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-2">
      <header className="flex items-baseline justify-between">
        <h3
          id={headingId}
          className="font-mono text-[10px] uppercase tracking-widest text-muted"
        >
          {t("polish_c.conflict_panel.active_heading")}
        </h3>
        <span className="font-sans text-[10px] text-muted">
          {t("polish_c.conflict_panel.active_summary", { count: items.length })}
        </span>
      </header>
      <ul className="flex flex-col gap-3">
        {items.map((conflict) => {
          const bulkSelectedFactId = bulkSelections.get(conflict.field) ?? null;
          const isInBulk = bulkSelectedFactId !== null;
          return (
            <li key={conflict.field}>
              <ConflictCard
                workspaceId={workspaceId}
                conflict={conflict}
                bulkSelectedFactId={bulkSelectedFactId}
                onBulkSelect={(chosenFactId) => onBulkSelect(conflict.field, chosenFactId)}
                bulkResolvePending={isInBulk && bulkResolvePending}
              />
            </li>
          );
        })}
      </ul>
    </section>
  );
}

interface ResolvedGroupProps {
  workspaceId: string;
  items: ReviewConflict[];
}

function ResolvedGroup({ workspaceId, items }: ResolvedGroupProps) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useLocalStorage<boolean>(
    RESOLVED_COLLAPSED_STORAGE_KEY,
    false,
  );
  const headingId = "polish-c-conflict-resolved-heading";
  const listId = "polish-c-conflict-resolved-list";
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-2">
      <header className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          aria-expanded={!collapsed}
          aria-controls={listId}
          className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-muted hover:text-ink focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3" aria-hidden />
          ) : (
            <ChevronDown className="h-3 w-3" aria-hidden />
          )}
          <span id={headingId}>{t("polish_c.conflict_panel.resolved_heading")}</span>
          <span className="sr-only">
            {collapsed
              ? t("polish_c.conflict_panel.resolved_expand")
              : t("polish_c.conflict_panel.resolved_collapse")}
          </span>
        </button>
        <span className="font-sans text-[10px] text-muted">
          {t("polish_c.conflict_panel.resolved_summary", { count: items.length })}
        </span>
      </header>
      {!collapsed && (
        <ul id={listId} className="flex flex-col gap-3">
          {items.map((conflict) => (
            <li key={conflict.field}>
              <ConflictCard workspaceId={workspaceId} conflict={conflict} />
            </li>
          ))}
        </ul>
      )}
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
  /**
   * Tier 3 §1.6: when this card is part of a pending bulk-resolve
   * mutation, the panel forwards `useBulkResolveConflicts().isPending`
   * here so the card can enter the "resolving" visual state. The card
   * never owns this flag — the live mutation hook is the source of truth.
   */
  bulkResolvePending?: boolean;
}

export function ConflictCard({
  workspaceId,
  conflict,
  bulkSelectedFactId = null,
  onBulkSelect,
  bulkResolvePending = false,
}: ConflictCardProps) {
  const { t } = useTranslation();
  const resolve = useResolveConflict(workspaceId);
  const defer = useDeferConflict(workspaceId);
  const [chosenFactId, setChosenFactId] = useState<number | null>(
    conflict.chosen_fact_id ?? null,
  );
  const [rationale, setRationale] = useState<string>(conflict.rationale ?? "");
  const [evidenceAck, setEvidenceAck] = useState<boolean>(
    conflict.evidence_ack ?? false,
  );
  const [showDeferForm, setShowDeferForm] = useState(false);
  const [deferRationale, setDeferRationale] = useState("");

  const candidates = conflict.candidates ?? [];
  const submittable =
    !conflict.resolved &&
    chosenFactId !== null &&
    rationale.trim().length >= 4 &&
    evidenceAck;
  const inBulk = bulkSelectedFactId !== null;
  const isDeferred = Boolean(conflict.deferred) && !conflict.re_surfaced_at;
  const isResurfaced = Boolean(conflict.deferred) && Boolean(conflict.re_surfaced_at);

  function handleDefer() {
    if (deferRationale.trim().length < 4) return;
    defer.mutate(
      { field: conflict.field, rationale: deferRationale.trim() },
      {
        onSuccess: () => {
          toastSuccess(
            t("review.conflict.deferred_toast_title"),
            t("review.conflict.deferred_toast_body", { label: conflict.label }),
          );
          setShowDeferForm(false);
          setDeferRationale("");
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("review.conflict.defer_error"));
          toastError(t("review.conflict.defer_error"), { description: e.message });
        },
      },
    );
  }

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

  // Tier 3 §1.6: derive a tri-state visual progression from the live
  // mutation hooks. `resolve.isPending` flips on at the moment we POST
  // /conflicts/resolve/ and flips off on success/error; same for
  // `defer.isPending` and (forwarded by the panel) `bulkResolvePending`.
  // No new state machinery — the mutation hook IS the state machine.
  const isMutating = resolve.isPending || defer.isPending || bulkResolvePending;
  const cardState: CardState = conflict.resolved
    ? "resolved"
    : isMutating
      ? "resolving"
      : "unresolved";
  const cardStateLabel =
    cardState === "resolving"
      ? t("polish_c.conflict_panel.state_resolving")
      : cardState === "resolved"
        ? t("polish_c.conflict_panel.state_resolved")
        : t("polish_c.conflict_panel.state_unresolved");

  return (
    <article
      aria-busy={cardState === "resolving"}
      className={cn(
        "rounded-md border bg-paper-2 p-3 transition-opacity",
        cardState === "resolved" && "border-accent/40",
        cardState === "resolving" && "border-muted/40 opacity-70",
        cardState === "unresolved" &&
          (conflict.required ? "border-danger/30" : "border-hairline-2"),
      )}
    >
      <span className="sr-only">
        {t("polish_c.conflict_panel.card_state_aria", { state: cardStateLabel })}
      </span>
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
          {cardState === "resolving" && (
            <span
              className="flex items-center gap-1 rounded-sm bg-muted/15 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-muted"
              aria-label={t("polish_c.conflict_panel.resolving_label")}
            >
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
              {t("polish_c.conflict_panel.state_resolving")}
            </span>
          )}
          {cardState === "resolved" && (
            <span className="flex items-center gap-1 rounded-sm bg-accent/15 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-accent-2">
              <Check
                className="h-3 w-3"
                aria-label={t("polish_c.conflict_panel.resolved_check_aria")}
              />
              {t("review.conflict.resolved_state")}
            </span>
          )}
          {isDeferred && (
            <span className="rounded-sm bg-info/15 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-info">
              {t("review.conflict.deferred_state")}
            </span>
          )}
          {isResurfaced && (
            <span className="rounded-sm bg-danger/15 px-1 py-0.5 font-sans text-[9px] uppercase tracking-wider text-danger">
              {t("review.conflict.resurfaced_state")}
            </span>
          )}
        </div>
      </header>
      {isDeferred && conflict.deferred_rationale && (
        <p className="mb-2 font-sans text-[10px] italic text-muted">
          &ldquo;{conflict.deferred_rationale}&rdquo;
          {conflict.deferred_by ? ` — ${conflict.deferred_by}` : null}
        </p>
      )}
      {isResurfaced && (
        <p className="mb-2 font-sans text-[10px] italic text-danger">
          {t("review.conflict.resurfaced_body")}
        </p>
      )}

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

              <div className="flex items-center justify-between gap-2">
                {!isDeferred && !showDeferForm && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDeferForm(true)}
                    disabled={resolve.isPending || defer.isPending}
                  >
                    {t("review.conflict.defer_action")}
                  </Button>
                )}
                <Button
                  variant="default"
                  size="sm"
                  disabled={!submittable || resolve.isPending}
                  onClick={handleSubmit}
                  className="ml-auto"
                >
                  {resolve.isPending
                    ? t("review.conflict.submit_pending")
                    : t("review.conflict.submit")}
                </Button>
              </div>
              {showDeferForm && (
                <div className="flex flex-col gap-2 border border-info/40 bg-paper-2 p-2">
                  <h4 className="font-mono text-[9px] uppercase tracking-widest text-info">
                    {t("review.conflict.defer_title")}
                  </h4>
                  <p className="font-sans text-[10px] text-muted">
                    {t("review.conflict.defer_body")}
                  </p>
                  <textarea
                    value={deferRationale}
                    onChange={(e) => setDeferRationale(e.target.value)}
                    disabled={defer.isPending}
                    rows={2}
                    placeholder={t("review.conflict.defer_rationale_placeholder")}
                    className="border border-hairline-2 bg-paper px-2 py-1 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowDeferForm(false);
                        setDeferRationale("");
                      }}
                      disabled={defer.isPending}
                    >
                      {t("review.conflict.defer_cancel")}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleDefer}
                      disabled={defer.isPending || deferRationale.trim().length < 4}
                    >
                      {defer.isPending
                        ? t("review.conflict.defer_saving")
                        : t("review.conflict.defer_save")}
                    </Button>
                  </div>
                </div>
              )}
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
