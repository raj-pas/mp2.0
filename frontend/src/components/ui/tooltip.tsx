/**
 * Radix Tooltip wrapper — Tier 3 production-quality polish (§1.10).
 *
 * Thin shadcn-pattern wrapper around `@radix-ui/react-tooltip`. Defaults:
 *   - `delayDuration={300}` so tooltips don't fire on accidental cursor
 *     traversal but still feel responsive when an advisor lingers.
 *   - `skipDelayDuration={150}` so consecutive tooltips in the same
 *     group activate quickly (Radix default).
 *   - `role="tooltip"` carried by Radix's `Content` primitive — paired
 *     with `aria-describedby` automatically when `<TooltipTrigger />`
 *     wraps the focusable target. (Verified against Radix docs v1.1.4.)
 *
 * Reduced-motion: the global `index.css` rule under
 * `@media (prefers-reduced-motion: reduce)` collapses Radix's `animate-in`
 * utilities to 1ms, so callers don't need per-component opt-outs.
 */
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as React from "react";

import { cn } from "../../lib/cn";

const TooltipProvider = ({
  delayDuration = 300,
  skipDelayDuration = 150,
  ...props
}: React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Provider>) => (
  <TooltipPrimitive.Provider
    delayDuration={delayDuration}
    skipDelayDuration={skipDelayDuration}
    {...props}
  />
);
TooltipProvider.displayName = "TooltipProvider";

/**
 * Single-tooltip shorthand. If callers don't render their own
 * `<TooltipProvider>` higher up the tree, the Root component
 * silently no-ops on hover. This wrapper accepts an optional
 * `delayDuration` per-instance override.
 */
const Tooltip = ({
  delayDuration = 300,
  ...props
}: React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Root>) => (
  <TooltipPrimitive.Root delayDuration={delayDuration} {...props} />
);
Tooltip.displayName = "Tooltip";

const TooltipTrigger = TooltipPrimitive.Trigger;

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 max-w-xs border border-hairline-2 bg-paper px-2 py-1 text-[11px] leading-snug text-ink shadow-md",
        "data-[state=delayed-open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=delayed-open]:fade-in-0",
        className,
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

export { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger };
