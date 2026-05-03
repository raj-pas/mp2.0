/**
 * Truncated — Tier 3 production-quality polish (§1.10).
 *
 * Renders `text` clipped to `max` characters with an ellipsis. The full
 * untruncated text is exposed via the Tooltip wrapper on hover/focus
 * (300ms delay default). When `text.length <= max` the component renders
 * the bare string with no tooltip overhead.
 *
 * Accessibility:
 *   - Trigger is a `<button type="button">` styled like inline text so
 *     keyboard users can focus the truncated label and Radix attaches
 *     `aria-describedby` to it pointing at the tooltip content. The
 *     button has no click handler — this is the standard idiom for
 *     "non-actionable but focusable for tooltip" per Radix docs.
 *   - Tooltip content carries Radix's built-in `role="tooltip"`.
 *   - `title` attribute is intentionally omitted — Radix's tooltip is
 *     the one a11y surface, and double-rendering tooltips in some
 *     browsers (native + Radix) is noisy for screen-reader users.
 *
 * Usage:
 *   <Truncated text={longString} max={80} className="text-[12px]" />
 *
 * The default 80-char ceiling is calibrated for the v36 ledger
 * surfaces (per-row note column, doc-name column).
 */
import * as React from "react";

import { cn } from "../lib/cn";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";

export interface TruncatedProps {
  text: string;
  max?: number;
  className?: string;
  /**
   * Optional override for the per-instance hover delay. Defaults to
   * the wrapper's 300ms.
   */
  delayDuration?: number;
}

export function Truncated({
  text,
  max = 80,
  className,
  delayDuration = 300,
}: TruncatedProps): React.ReactElement {
  const needsTruncation = text.length > max;
  if (!needsTruncation) {
    return <span className={className}>{text}</span>;
  }
  const truncated = `${text.slice(0, Math.max(0, max - 1))}…`;
  return (
    <TooltipProvider delayDuration={delayDuration}>
      <Tooltip delayDuration={delayDuration}>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label={text}
            className={cn(
              "inline-block max-w-full cursor-help truncate bg-transparent p-0 text-left align-bottom font-inherit text-inherit focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent",
              className,
            )}
          >
            {truncated}
          </button>
        </TooltipTrigger>
        <TooltipContent>{text}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default Truncated;
