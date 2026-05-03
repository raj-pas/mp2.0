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
import { X } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { ConfidenceChip } from "../components/ConfidenceChip";
import { Skeleton } from "../components/ui/skeleton";
import {
  type ContributedFact,
  type ReviewDocumentDetail,
  useReviewDocument,
} from "../lib/review";
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
  const open = documentId !== null;

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
          {detail.data && <ContributedFactsList facts={detail.data.contributed_facts} />}
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
}

function ContributedFactsList({ facts }: ContributedFactsListProps) {
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
              <FactRow key={fact.fact_id} fact={fact} />
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}

function FactRow({ fact }: { fact: ContributedFact }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1 border border-hairline-2 bg-paper-2 p-2">
      <div className="flex items-baseline justify-between gap-2">
        <dt className="font-sans text-[12px] text-ink">{fact.label}</dt>
        <ConfidenceChip level={fact.confidence} />
      </div>
      <dd className="font-mono text-[12px] text-ink">{formatFactValue(fact.value)}</dd>
      {fact.source_page !== null && (
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("doc_detail.source_page", { page: fact.source_page })}
        </p>
      )}
      {fact.redacted_evidence_quote && (
        <blockquote className="border-l-2 border-hairline pl-2 font-sans text-[11px] italic text-muted">
          {fact.redacted_evidence_quote}
        </blockquote>
      )}
    </div>
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
