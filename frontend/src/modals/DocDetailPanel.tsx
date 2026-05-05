/**
 * Phase 5b.5 — Per-document detail slide-out (UX dimension B.1).
 *
 * Triggered when an advisor clicks a doc row in `ProcessingPanel`.
 * Slides in from the right edge so the parent ReviewScreen stays
 * visible underneath; advisors can scan multiple docs by clicking
 * each in sequence without losing the workspace context.
 *
 * Codifies the design-system pattern "slide-out for contextual
 * deep-dive without losing parent context" (per
 * docs/agent/design-system.md Phase 5c).
 *
 * A11y: focus moves to the close button on open; Escape closes;
 * click-outside-on-overlay closes; contributed facts are
 * grouped by section with a `<dl>` semantic structure so screen
 * readers narrate the relationship.
 */
import { Pencil, Plus, X } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { ConfidenceChip } from "../components/ConfidenceChip";
import { FactInput } from "../components/FactInput";
import { Skeleton } from "../components/ui/skeleton";
import {
  type ContributedFact,
  type ReviewDocumentDetail,
  useApplyFactOverride,
  useReviewDocument,
} from "../lib/review";
import { normalizeApiError } from "../lib/api-error";
import {
  CANONICAL_FIELD_AUTOCOMPLETE,
  type CanonicalFieldShape,
  getCanonicalFieldShape,
} from "../lib/canonical-fields";
import { toastError, toastSuccess } from "../lib/toast";
import { cn } from "../lib/cn";

interface DocDetailPanelProps {
  workspaceId: string;
  documentId: number | null;
  onClose: () => void;
}

export function DocDetailPanel({ workspaceId, documentId, onClose }: DocDetailPanelProps) {
  const { t } = useTranslation();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const detail = useReviewDocument(workspaceId, documentId);
  const applyOverride = useApplyFactOverride(workspaceId);
  const open = documentId !== null;
  const [editingFieldId, setEditingFieldId] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);

  // Focus the close button + bind Escape on open.
  useEffect(() => {
    if (!open) return;
    closeButtonRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop — click closes; semi-transparent so the parent
          ReviewScreen still reads visually as the page context. */}
      <div
        aria-hidden
        onClick={onClose}
        className="fixed inset-0 z-40 bg-ink/20"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="doc-detail-title"
        className={cn(
          "fixed right-0 top-0 z-50 flex h-screen w-[420px] max-w-full flex-col",
          "border-l border-hairline-2 bg-paper shadow-xl",
          "motion-safe:animate-[slideInFromRight_180ms_ease-out]",
        )}
      >
        <header className="flex items-baseline justify-between border-b border-hairline-2 px-4 py-3">
          <div className="flex flex-col">
            <h2
              id="doc-detail-title"
              className="font-serif text-base font-medium tracking-tight text-ink"
            >
              {detail.data?.original_filename ?? t("doc_detail.loading")}
            </h2>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {detail.data?.document_type ?? "—"}
            </p>
          </div>
          <Button
            ref={closeButtonRef}
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("doc_detail.close")}
          >
            <X aria-hidden className="h-4 w-4" />
          </Button>
        </header>
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
          {detail.isPending && <DocDetailSkeleton />}
          {detail.isError && (
            <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
              {t("doc_detail.load_error")}
            </p>
          )}
          {detail.data && (
            <ContributedFactsList
              facts={detail.data.contributed_facts}
              editingFieldId={editingFieldId}
              onEdit={setEditingFieldId}
              onSubmitEdit={(fact, value, rationale) => {
                applyOverride.mutate(
                  { field: fact.field, value, rationale, is_added: false },
                  {
                    onSuccess: (response) => {
                      setEditingFieldId(null);
                      toastSuccess(
                        t("doc_detail.edit_saved_title"),
                        t("doc_detail.edit_saved_body", {
                          label: fact.label,
                          invalidated: response.invalidated_approvals.join(", ") || "—",
                        }),
                      );
                    },
                    onError: (err) => {
                      const e = normalizeApiError(err, t("doc_detail.edit_error"));
                      toastError(t("doc_detail.edit_error"), { description: e.message });
                    },
                  },
                );
              }}
              submitting={applyOverride.isPending}
            />
          )}
          {detail.data && (
            <AddFactSection
              adding={adding}
              onToggle={() => setAdding((v) => !v)}
              submitting={applyOverride.isPending}
              onSubmit={(field, value, rationale) => {
                applyOverride.mutate(
                  { field, value, rationale, is_added: true },
                  {
                    onSuccess: () => {
                      setAdding(false);
                      toastSuccess(
                        t("doc_detail.add_saved_title"),
                        t("doc_detail.add_saved_body", { field }),
                      );
                    },
                    onError: (err) => {
                      const e = normalizeApiError(err, t("doc_detail.add_error"));
                      toastError(t("doc_detail.add_error"), { description: e.message });
                    },
                  },
                );
              }}
            />
          )}
        </div>
      </aside>
    </>
  );
}

function DocDetailSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-16 w-full" />
    </div>
  );
}

interface ContributedFactsListProps {
  facts: ReviewDocumentDetail["contributed_facts"];
  editingFieldId: number | null;
  onEdit: (fact_id: number | null) => void;
  onSubmitEdit: (fact: ContributedFact, value: string, rationale: string) => void;
  submitting: boolean;
}

function ContributedFactsList({
  facts,
  editingFieldId,
  onEdit,
  onSubmitEdit,
  submitting,
}: ContributedFactsListProps) {
  const { t } = useTranslation();
  const grouped = useMemo(() => groupBySection(facts), [facts]);
  if (facts.length === 0) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("doc_detail.no_contributed")}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {grouped.map(([section, sectionFacts]) => (
        <section key={section} aria-labelledby={`doc-detail-${section}`}>
          <h3
            id={`doc-detail-${section}`}
            className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted"
          >
            {t(`doc_detail.section.${section}`, { defaultValue: section })}
          </h3>
          <dl className="flex flex-col gap-2">
            {sectionFacts.map((fact) => (
              <FactRow
                key={fact.fact_id}
                fact={fact}
                editing={editingFieldId === fact.fact_id}
                onEdit={() => onEdit(fact.fact_id)}
                onCancelEdit={() => onEdit(null)}
                onSubmit={(value, rationale) => onSubmitEdit(fact, value, rationale)}
                submitting={submitting}
              />
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}

function FactRow({
  fact,
  editing,
  onEdit,
  onCancelEdit,
  onSubmit,
  submitting,
}: {
  fact: ContributedFact;
  editing: boolean;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSubmit: (value: string, rationale: string) => void;
  submitting: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1 border border-hairline-2 bg-paper-2 p-2">
      <div className="flex items-baseline justify-between gap-2">
        <dt className="font-sans text-[12px] text-ink">{fact.label}</dt>
        <div className="flex items-center gap-2">
          <ConfidenceChip level={fact.confidence} />
          {!editing && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onEdit}
              aria-label={t("doc_detail.edit_aria", { label: fact.label })}
            >
              <Pencil aria-hidden className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>
      {!editing && (
        <dd className="font-mono text-[12px] text-ink">{formatFactValue(fact.value)}</dd>
      )}
      {!editing && fact.source_page !== null && (
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("doc_detail.source_page", { page: fact.source_page })}
        </p>
      )}
      {!editing && fact.redacted_evidence_quote && (
        <blockquote className="border-l-2 border-hairline pl-2 font-sans text-[11px] italic text-muted">
          {fact.redacted_evidence_quote}
        </blockquote>
      )}
      {editing && (
        <FactEditForm
          fieldPath={fact.field}
          initialValue={formatFactValue(fact.value)}
          onCancel={onCancelEdit}
          onSubmit={onSubmit}
          submitting={submitting}
        />
      )}
    </div>
  );
}

function FactEditForm({
  fieldPath,
  initialValue,
  onCancel,
  onSubmit,
  submitting,
}: {
  fieldPath: string;
  initialValue: string;
  onCancel: () => void;
  onSubmit: (value: string, rationale: string) => void;
  submitting: boolean;
}) {
  const { t } = useTranslation();
  const shape = useMemo(() => getCanonicalFieldShape(fieldPath), [fieldPath]);
  const [value, setValue] = useState(() => normalizeInitialValue(initialValue, shape));
  const [rationale, setRationale] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  function validate(next: string): string | null {
    if (next.trim().length === 0) return t("doc_detail.value_required");
    if (shape.kind === "number") {
      const parsed = Number(next);
      if (Number.isNaN(parsed)) return t("doc_detail.value_must_be_number");
      if (shape.min !== undefined && parsed < shape.min) {
        return t("doc_detail.value_below_min", { min: shape.min });
      }
      if (shape.max !== undefined && parsed > shape.max) {
        return t("doc_detail.value_above_max", { max: shape.max });
      }
    }
    return null;
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const error = validate(value);
    if (error || rationale.trim().length < 4) {
      setValidationError(error);
      return;
    }
    onSubmit(value.trim(), rationale.trim());
  }

  return (
    <form className="flex flex-col gap-2" onSubmit={handleSubmit}>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("doc_detail.edit_value_label")}
        </span>
        <FactInput
          fieldPath={fieldPath}
          value={value}
          onChange={(next) => {
            setValue(next);
            setValidationError(null);
          }}
          disabled={submitting}
          focusOnMount
          selectPlaceholder={t("doc_detail.value_select_placeholder")}
        />
        {validationError && (
          <span role="alert" className="font-mono text-[10px] text-danger">
            {validationError}
          </span>
        )}
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("doc_detail.edit_rationale_label")}
        </span>
        <textarea
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          disabled={submitting}
          rows={2}
          placeholder={t("doc_detail.edit_rationale_placeholder")}
          className="border border-hairline-2 bg-paper px-2 py-1 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
        />
      </label>
      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={submitting}>
          {t("doc_detail.edit_cancel")}
        </Button>
        <Button
          type="submit"
          size="sm"
          disabled={
            submitting ||
            value.trim().length === 0 ||
            rationale.trim().length < 4 ||
            validationError !== null
          }
        >
          {submitting ? t("doc_detail.edit_saving") : t("doc_detail.edit_save")}
        </Button>
      </div>
    </form>
  );
}

function normalizeInitialValue(raw: string, shape: CanonicalFieldShape): string {
  if (shape.kind === "date") {
    // Try to coerce ISO-prefixed strings; the backend stores
    // YYYY-MM-DD on date facts but the wire shape may include
    // time + zone for asserted_at. Strip time portion if present.
    const isoPrefixMatch = raw.match(/^\d{4}-\d{2}-\d{2}/);
    return isoPrefixMatch ? isoPrefixMatch[0] : "";
  }
  if (shape.kind === "number") {
    const parsed = Number(raw);
    return Number.isNaN(parsed) ? "" : String(parsed);
  }
  if (shape.kind === "enum" && shape.enum_options) {
    const lower = raw.trim().toLowerCase();
    const match = shape.enum_options.find((option) => option.value === lower);
    return match ? match.value : "";
  }
  return raw;
}

function AddFactSection({
  adding,
  onToggle,
  submitting,
  onSubmit,
}: {
  adding: boolean;
  onToggle: () => void;
  submitting: boolean;
  onSubmit: (field: string, value: string, rationale: string) => void;
}) {
  const { t } = useTranslation();
  const [field, setField] = useState("");
  const [value, setValue] = useState("");
  const [rationale, setRationale] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (field.trim().length === 0 || value.trim().length === 0 || rationale.trim().length < 4)
      return;
    onSubmit(field.trim(), value.trim(), rationale.trim());
  }

  if (!adding) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={onToggle}
        className="self-start"
      >
        <Plus aria-hidden className="mr-1 h-3 w-3" />
        {t("doc_detail.add_action")}
      </Button>
    );
  }
  return (
    <form
      className="flex flex-col gap-2 border border-accent/40 bg-paper-2 p-3"
      onSubmit={handleSubmit}
    >
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-accent">
        {t("doc_detail.add_title")}
      </h3>
      <p className="font-sans text-[11px] text-muted">{t("doc_detail.add_body")}</p>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("doc_detail.add_field_label")}
        </span>
        <input
          list="doc-detail-add-field-suggestions"
          type="text"
          value={field}
          onChange={(e) => {
            setField(e.target.value);
            setValue("");
          }}
          disabled={submitting}
          placeholder={t("doc_detail.add_field_placeholder")}
          className="border border-hairline-2 bg-paper px-2 py-1 font-mono text-[12px] text-ink focus:border-accent focus:outline-none"
        />
        <datalist id="doc-detail-add-field-suggestions">
          {CANONICAL_FIELD_AUTOCOMPLETE.map((path) => (
            <option key={path} value={path} />
          ))}
        </datalist>
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("doc_detail.edit_value_label")}
        </span>
        <FactInput
          fieldPath={field}
          value={value}
          onChange={setValue}
          disabled={submitting || field.length === 0}
          selectPlaceholder={t("doc_detail.value_select_placeholder")}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("doc_detail.edit_rationale_label")}
        </span>
        <textarea
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          disabled={submitting}
          rows={2}
          placeholder={t("doc_detail.add_rationale_placeholder")}
          className="border border-hairline-2 bg-paper px-2 py-1 font-sans text-[11px] text-ink focus:border-accent focus:outline-none"
        />
      </label>
      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onToggle} disabled={submitting}>
          {t("doc_detail.add_cancel")}
        </Button>
        <Button
          type="submit"
          size="sm"
          disabled={
            submitting ||
            field.trim().length === 0 ||
            value.trim().length === 0 ||
            rationale.trim().length < 4
          }
        >
          {submitting ? t("doc_detail.add_saving") : t("doc_detail.add_save")}
        </Button>
      </div>
    </form>
  );
}

function groupBySection(facts: ContributedFact[]): [string, ContributedFact[]][] {
  const groups = new Map<string, ContributedFact[]>();
  for (const fact of facts) {
    const list = groups.get(fact.section) ?? [];
    list.push(fact);
    groups.set(fact.section, list);
  }
  return Array.from(groups.entries());
}

function formatFactValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}
