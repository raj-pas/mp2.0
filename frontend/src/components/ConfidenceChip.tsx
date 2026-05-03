/**
 * ConfidenceChip — single-source rendering for fact extraction
 * confidence (Phase 5b.9, locked 2026-05-02).
 *
 * Tied to canonical Confidence triple ("high"/"medium"/"low") used
 * across `extraction.schemas.BedrockFact`, `ExtractedFact`, and
 * `ConflictCandidate`. Color-coded with text label (NOT color-only —
 * a11y discipline; matches WCAG 2.1 AA).
 */
import { useTranslation } from "react-i18next";

import { cn } from "../lib/cn";

type Confidence = "high" | "medium" | "low";

interface ConfidenceChipProps {
  level: Confidence;
  className?: string;
}

const LEVEL_STYLES: Record<Confidence, string> = {
  high: "bg-accent/15 text-accent-2 border-accent/40",
  medium: "bg-ink/5 text-muted border-hairline-2",
  low: "bg-danger/10 text-danger border-danger/30",
};

export function ConfidenceChip({ level, className }: ConfidenceChipProps) {
  const { t } = useTranslation();
  return (
    <span
      role="status"
      aria-label={t(`confidence.aria_${level}` as const)}
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 font-sans text-[9px] uppercase tracking-wider",
        LEVEL_STYLES[level],
        className,
      )}
    >
      {t(`confidence.${level}` as const)}
    </span>
  );
}
