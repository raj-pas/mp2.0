/**
 * ToggleCurrentIdeal — segmented control for HouseholdRoute treemap
 * dataset (plan v20 §A1.35 / G9 — P7).
 *
 * Mirrors the visual + a11y idiom of `<ModeToggle>` /
 * `<ToggleFundAssetClass>`. When `disabled` is true (no PortfolioRun
 * exists yet), the "Ideal" option is rendered with `aria-disabled` +
 * tooltip per §A1.35 ("Generate a portfolio first"), and the persisted
 * value is forced back to "current" so consumers don't try to read
 * recommended allocation from a null run.
 *
 * Persistence: per-user global localStorage (per §A1.14 #14 — NO
 * household-id namespace). Same key shared across HouseholdRoute
 * mounts so toggling persists across reload.
 *
 * Theme tokens: `--ink` / `--paper-2` / `--accent-2` per sister §3.10.
 */
import { useTranslation } from "react-i18next";

import { cn } from "../lib/cn";
import { useLocalStorage } from "../lib/local-storage";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";

export type CurrentIdealMode = "current" | "ideal";

export const STORAGE_CURRENT_IDEAL = "mp20_view_mode_current_vs_ideal";

/**
 * `useCurrentIdealMode()` — consumer hook for the persisted view mode.
 * Default `"current"` (concrete-first, matches `ToggleFundAssetClass`).
 */
export function useCurrentIdealMode(): readonly [
  CurrentIdealMode,
  (next: CurrentIdealMode) => void,
] {
  return useLocalStorage<CurrentIdealMode>(STORAGE_CURRENT_IDEAL, "current");
}

interface ToggleCurrentIdealProps {
  /** When true, the "Ideal" option is disabled with tooltip + the
   *  effective value is coerced to "current". */
  disabled?: boolean;
  /** Override the persisted value (controlled mode). */
  value?: CurrentIdealMode;
  /** Override the persisted setter (controlled mode). */
  onChange?: (next: CurrentIdealMode) => void;
}

export function ToggleCurrentIdeal({
  disabled = false,
  value,
  onChange,
}: ToggleCurrentIdealProps = {}) {
  const { t } = useTranslation();
  const [persisted, setPersisted] = useCurrentIdealMode();
  // Coerce to "current" when disabled — guards downstream reads of a
  // null PortfolioRun.recommended_allocation per §A1.35.
  const rawCurrent = value ?? persisted;
  const current: CurrentIdealMode = disabled ? "current" : rawCurrent;
  const setCurrent = onChange ?? setPersisted;
  const options: { value: CurrentIdealMode; label: string }[] = [
    { value: "current", label: t("toggle.current_ideal.current") },
    { value: "ideal", label: t("toggle.current_ideal.ideal") },
  ];
  return (
    <TooltipProvider>
      <div
        className="flex items-center gap-2"
        role="group"
        aria-label={t("toggle.current_ideal.aria_label")}
      >
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("toggle.current_ideal.label")}
        </span>
        <div className="inline-flex border border-hairline bg-paper-2 p-0.5">
          {options.map((opt) => {
            const on = opt.value === current;
            const optDisabled = disabled && opt.value === "ideal";
            const button = (
              <button
                key={opt.value}
                type="button"
                data-on={on}
                data-testid={`toggle-current-ideal-${opt.value}`}
                aria-pressed={on}
                aria-disabled={optDisabled || undefined}
                disabled={optDisabled}
                onClick={() => {
                  if (optDisabled) return;
                  setCurrent(opt.value);
                }}
                className={cn(
                  "px-2.5 py-1 font-sans text-[11px] font-medium transition-colors",
                  on ? "bg-ink text-paper" : "text-muted hover:text-ink",
                  optDisabled && "cursor-not-allowed opacity-50",
                )}
              >
                {opt.label}
              </button>
            );
            if (optDisabled) {
              // Radix's TooltipTrigger asChild requires a focusable child to
              // surface the tooltip on keyboard focus. The disabled <button>
              // already accepts focus when `aria-disabled` is set without the
              // native disabled attribute clobbering it; we keep `disabled`
              // for click semantics but rely on the wrapping span for hover.
              return (
                <Tooltip key={opt.value}>
                  <TooltipTrigger asChild>
                    <span>{button}</span>
                  </TooltipTrigger>
                  <TooltipContent>{t("toggle.current_ideal.disabled_tooltip")}</TooltipContent>
                </Tooltip>
              );
            }
            return button;
          })}
        </div>
      </div>
    </TooltipProvider>
  );
}
