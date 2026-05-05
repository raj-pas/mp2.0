/**
 * UnallocatedBanner — plan v20 §A1.36 (P12 / G12 / G13).
 *
 * Renders ABOVE the action sub-bar (per §A1.18 LOCKED layout) when ANY
 * Purpose-held account in the household has unallocated balance —
 * `account.current_value > sum(legs.allocated_amount)` — so the
 * advisor sees the gap that the BlockerBanner names but the treemap
 * (pre-P12) didn't visualize.
 *
 * UX (per design-system §1 / Stripe Connect KYC banner pattern):
 *   - Short headline ("$X unallocated") + per-account detail.
 *   - CTA "Assign now →" that opens AssignAccountModal pre-focused on
 *     the affected account (per §A1.14 #10). For now P13 has not yet
 *     shipped the modal, so the CTA stubs to `console.log` + a
 *     toast — the call signature is locked so P13 only needs to wire
 *     the modal's `open()` API.
 *
 * Backwards-compat (sister §3.16): household with NO unallocated
 * balance returns `null` (no banner). Household with `account_id` of
 * `null` (legacy synthetic data) safely degrades to no CTA.
 *
 * Z-order coord: this banner is z-10. Sister's StaleRunOverlay is
 * z-20 so it always sits ABOVE this banner. Per-LOC §A1.18.
 */
import { AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import type { Account, HouseholdDetail } from "../lib/household";
import { formatCad } from "../lib/format";
import { toastSuccess } from "../lib/toast";

export type UnallocatedAccountSummary = {
  account_id: string;
  account_label: string;
  current_value: number;
  allocated_amount: number;
  unallocated_amount: number;
};

/**
 * Pure helper exported for test reuse: derive per-account unallocated
 * summary from a household. Empty-array result = household is fully
 * allocated → banner returns `null`.
 */
export function unallocatedAccountsForHousehold(
  household: Pick<HouseholdDetail, "accounts" | "goals">,
): UnallocatedAccountSummary[] {
  const linksByAccount = new Map<string, number>();
  for (const goal of household.goals) {
    for (const link of goal.account_allocations) {
      const sum = linksByAccount.get(link.account_id) ?? 0;
      linksByAccount.set(link.account_id, sum + (Number(link.allocated_amount) || 0));
    }
  }
  return household.accounts
    .filter((account) => account.is_held_at_purpose)
    .map((account: Account) => {
      const allocated = linksByAccount.get(account.id) ?? 0;
      const unallocated = Number(account.current_value) - allocated;
      return {
        account_id: account.id,
        account_label: account.type,
        current_value: Number(account.current_value),
        allocated_amount: allocated,
        unallocated_amount: unallocated,
      };
    })
    .filter((row) => row.unallocated_amount > 1); // $1 tolerance
}

interface UnallocatedBannerProps {
  household: Pick<HouseholdDetail, "accounts" | "goals">;
  /**
   * Click handler invoked when the advisor clicks the "Assign now"
   * CTA or a per-account "Assign" link. P13 will pass the actual
   * `AssignAccountModal.open()` callable; for now the parent route
   * stubs to `console.log` + toast. Signature is locked so P13 only
   * needs to drop in the real implementation.
   */
  onAssignClick?: (params: { account_id: string }) => void;
}

export function UnallocatedBanner({ household, onAssignClick }: UnallocatedBannerProps) {
  const { t } = useTranslation();
  const rows = unallocatedAccountsForHousehold(household);
  if (rows.length === 0) return null;
  const totalUnallocated = rows.reduce((s, r) => s + r.unallocated_amount, 0);
  const handleClick = (account_id: string) => {
    if (onAssignClick !== undefined) {
      onAssignClick({ account_id });
      return;
    }
    // P13 placeholder — log + toast so the click is reachable in tests
    // and the advisor sees feedback. Replaced when AssignAccountModal
    // lands in Pair 5.
    toastSuccess(
      t("unallocated_banner.stub_toast_title"),
      t("unallocated_banner.stub_toast_body"),
    );
  };

  return (
    <section
      aria-label={t("unallocated_banner.aria_label")}
      data-testid="unallocated-banner"
      className="relative z-10 flex flex-col gap-2 border border-warning bg-paper-2 px-5 py-3 shadow-sm"
    >
      <div className="flex items-baseline gap-3">
        <AlertCircle aria-hidden className="h-4 w-4 text-warning" />
        <h2 className="font-serif text-base text-ink">
          {t("unallocated_banner.headline", { amount: formatCad(totalUnallocated) })}
        </h2>
      </div>
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("unallocated_banner.body")}
      </p>
      <ul className="flex flex-col gap-1">
        {rows.map((row) => (
          <li
            key={row.account_id}
            className="flex items-center justify-between font-sans text-[12px] text-ink"
          >
            <span>
              {t("unallocated_banner.row_summary", {
                account: row.account_label,
                unallocated: formatCad(row.unallocated_amount),
              })}
              <span className="ml-2 font-mono text-[10px] text-muted">
                {t("unallocated_banner.row_breakdown", {
                  allocated: formatCad(row.allocated_amount),
                  current: formatCad(row.current_value),
                })}
              </span>
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleClick(row.account_id)}
              aria-label={t("unallocated_banner.cta_per_account_aria", {
                account: row.account_label,
              })}
            >
              {t("unallocated_banner.cta")}
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
