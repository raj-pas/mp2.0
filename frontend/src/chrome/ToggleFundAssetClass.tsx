/**
 * ToggleFundAssetClass — segmented control for AllocationBars view mode
 * (plan v20 §A1.35 / G8 — P6).
 *
 * Mirrors the visual + a11y idiom of `<ModeToggle>` (chrome/ModeToggle):
 *   - role="group" wrapper with `aria-label`
 *   - inner row of <button type="button" aria-pressed={on}> options
 *   - `data-on={on}` for visual-verification snapshots
 *
 * Persistence: per-user global localStorage (per §A1.14 #14 — NO
 * household-id namespace). The same key is shared across AccountRoute
 * + GoalRoute so toggling on one route persists on the other.
 *
 * Theme tokens: `--ink` / `--paper-2` / `--accent-2` per sister §3.10.
 */
import { useTranslation } from "react-i18next";

import { cn } from "../lib/cn";
import { useLocalStorage } from "../lib/local-storage";

export type FundAssetMode = "fund" | "asset_class";

export const STORAGE_FUND_ASSET = "mp20_view_mode_fund_vs_asset";

/**
 * `useFundAssetMode()` — consumer hook for the persisted view mode.
 * Default `"fund"` (concrete-first, per A6 cognitive-load discipline).
 */
export function useFundAssetMode(): readonly [FundAssetMode, (next: FundAssetMode) => void] {
  return useLocalStorage<FundAssetMode>(STORAGE_FUND_ASSET, "fund");
}

interface ToggleFundAssetClassProps {
  /** Override the persisted value (controlled mode). */
  value?: FundAssetMode;
  /** Override the persisted setter (controlled mode). */
  onChange?: (next: FundAssetMode) => void;
}

export function ToggleFundAssetClass({ value, onChange }: ToggleFundAssetClassProps = {}) {
  const { t } = useTranslation();
  const [persisted, setPersisted] = useFundAssetMode();
  const current = value ?? persisted;
  const setCurrent = onChange ?? setPersisted;
  const options: { value: FundAssetMode; label: string }[] = [
    { value: "fund", label: t("toggle.fund_asset.fund") },
    { value: "asset_class", label: t("toggle.fund_asset.asset_class") },
  ];
  return (
    <div
      className="flex items-center gap-2"
      role="group"
      aria-label={t("toggle.fund_asset.aria_label")}
    >
      <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
        {t("toggle.fund_asset.label")}
      </span>
      <div className="inline-flex border border-hairline bg-paper-2 p-0.5">
        {options.map((opt) => {
          const on = opt.value === current;
          return (
            <button
              key={opt.value}
              type="button"
              data-on={on}
              data-testid={`toggle-fund-asset-${opt.value}`}
              aria-pressed={on}
              onClick={() => setCurrent(opt.value)}
              className={cn(
                "px-2.5 py-1 font-sans text-[11px] font-medium transition-colors",
                on ? "bg-ink text-paper" : "text-muted hover:text-ink",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
