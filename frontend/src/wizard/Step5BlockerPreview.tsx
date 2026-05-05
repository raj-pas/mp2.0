/**
 * Pre-commit blocker preview (P14 / §A1.20 lazy-loaded).
 *
 * Renders a structured `PortfolioGenerationBlocker` list — the same
 * shape that P11 emits server-side after commit — so the advisor sees
 * the SAME copy in the wizard as on HouseholdRoute post-commit.
 *
 * Cross-phase contract (§A1.51 P11×P14): the JSON shape rendered here
 * MUST match P11's `web/api/types.py` `PortfolioGenerationBlocker`
 * TypedDict byte-for-byte. P11 ships the backend type; this component
 * mirrors it locally (same field names, same `code` literals, same
 * `ui_action` literals) so the two surfaces stay in lockstep.
 *
 * Lazy-loaded (§A1.20 budget): the parent `Step5Review.tsx` imports
 * this via `React.lazy(() => import("./Step5BlockerPreview"))`, so it
 * only ships in the bundle chunk that loads when the advisor reaches
 * Step 5. Target chunk size: <100 kB gzipped (well under the §A1.20
 * cap; this module is small).
 */
import { useFormContext, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { type WizardDraft } from "./schema";
import { formatCadCompact } from "../lib/format";

/**
 * Local mirror of `web/api/types.py:PortfolioGenerationBlocker`.
 *
 * P11 (sub-agent A) ships the backend TypedDict as `web/api/types.py`
 * and re-exports through `frontend/src/lib/household.ts`. Until P11
 * lands, we keep this local mirror so P14 can ship without a build
 * break. After P11 commits, this type collapses into the imported one
 * (same shape; no migration needed).
 *
 * Contract test: `Step5Review.test.tsx::test_pre_commit_blocker_preview_matches_p11_backend_shape_byte_for_byte`
 * asserts that the rendered JSON shape mirrors §A1.27 TypedDict.
 */
export type PortfolioGenerationBlockerCode =
  | "purpose_account_unassigned"
  | "purpose_account_unallocated"
  | "purpose_account_zero_value"
  | "purpose_account_pct_not_100"
  | "goal_missing_target_date"
  | "goal_missing_target_amount"
  | "goal_invalid_risk_score"
  | "goal_zero_legs"
  | "household_invalid_risk_score"
  | "no_accounts"
  | "no_goals"
  | "unsupported_account_type"
  | "missing_link_amount"
  | "mixed_amount_pct";

export type PortfolioGenerationBlockerUiAction =
  | "assign_to_goal"
  | "edit_account_value"
  | "set_goal_horizon"
  | "set_goal_target"
  | "set_household_risk"
  | "open_review_workspace";

export interface PortfolioGenerationBlocker {
  code: PortfolioGenerationBlockerCode;
  account_id?: string;
  account_label?: string;
  account_value_basis_points?: number;
  account_unallocated_basis_points?: number;
  goal_id?: string;
  goal_label?: string;
  ui_action: PortfolioGenerationBlockerUiAction;
}

/**
 * Compute the structured blockers for a wizard draft.
 *
 * Mirrors `web/api/review_state.py:portfolio_generation_blockers_for_household`
 * branch-for-branch so the wizard preview matches the post-commit
 * banner exactly. Two cases we materialize here:
 *
 *   - `purpose_account_unallocated` — sum of legs ≠ account value
 *   - `goal_missing_target_amount` — goal has no positive target
 *   - `goal_zero_legs` — goal has no positive leg
 *
 * (These are the cases P14 hard-blocks at the schema level. Other P11
 * codes — e.g. `unsupported_account_type` — only fire post-commit
 * because the wizard's own field validation already excludes them.)
 */
export function computeWizardBlockers(
  draft: Pick<WizardDraft, "accounts" | "goals">,
): PortfolioGenerationBlocker[] {
  const blockers: PortfolioGenerationBlocker[] = [];
  const accounts = draft.accounts ?? [];
  const goals = draft.goals ?? [];

  // Account-centric: unallocated balance.
  for (let accIdx = 0; accIdx < accounts.length; accIdx++) {
    const account = accounts[accIdx];
    if (account === undefined) continue;
    const acctValue = Number(account.current_value);
    if (!Number.isFinite(acctValue) || acctValue <= 0) continue;
    let allocated = 0;
    for (const goal of goals) {
      for (const leg of goal.legs) {
        if (leg.account_index === accIdx) {
          const legAmount = Number(leg.allocated_amount);
          if (Number.isFinite(legAmount)) allocated += legAmount;
        }
      }
    }
    if (Math.abs(allocated - acctValue) > 0.01) {
      const unallocated = acctValue - allocated;
      blockers.push({
        code: "purpose_account_unallocated",
        account_id: `wizard_account_${accIdx}`,
        account_label: `${account.account_type} #${accIdx + 1}`,
        // basis-point integer encoding mirrors §A1.27 (Decimal → int *
        // 100 — i.e. 1 cent = 1 basis-point of $1). This matches the
        // server-side encoding so a future shared lib/schemas.ts type
        // can flow either direction.
        account_value_basis_points: Math.round(acctValue * 100),
        account_unallocated_basis_points: Math.round(unallocated * 100),
        ui_action: "assign_to_goal",
      });
    }
  }

  // Goal-side: missing target_amount + zero legs.
  for (let gIdx = 0; gIdx < goals.length; gIdx++) {
    const goal = goals[gIdx];
    if (goal === undefined) continue;
    const goalLabel = goal.name || `Goal ${gIdx + 1}`;
    const targetAmount = Number(goal.target_amount);
    if (
      !goal.target_amount ||
      !Number.isFinite(targetAmount) ||
      targetAmount <= 0
    ) {
      blockers.push({
        code: "goal_missing_target_amount",
        goal_id: `wizard_goal_${gIdx}`,
        goal_label: goalLabel,
        ui_action: "set_goal_target",
      });
    }
    const hasPositiveLeg = goal.legs.some((leg) => {
      const amount = Number(leg.allocated_amount);
      return Number.isFinite(amount) && amount > 0;
    });
    if (!hasPositiveLeg) {
      blockers.push({
        code: "goal_zero_legs",
        goal_id: `wizard_goal_${gIdx}`,
        goal_label: goalLabel,
        ui_action: "assign_to_goal",
      });
    }
  }

  return blockers;
}

interface DraftLike {
  accounts?: WizardDraft["accounts"] | undefined;
  goals?: WizardDraft["goals"] | undefined;
}

function normalizeDraft(draft: DraftLike): Pick<WizardDraft, "accounts" | "goals"> {
  return {
    accounts: (draft.accounts ?? []).map((a) => ({
      account_type: a?.account_type ?? "Non-Registered",
      current_value: a?.current_value ?? "",
      custodian: a?.custodian ?? "",
      missing_holdings_confirmed: a?.missing_holdings_confirmed ?? false,
    })) as WizardDraft["accounts"],
    goals: (draft.goals ?? []).map((g) => ({
      name: g?.name ?? "",
      target_date: g?.target_date ?? "",
      necessity_score: g?.necessity_score ?? 3,
      target_amount: g?.target_amount ?? "",
      legs: (g?.legs ?? []).map((l) => ({
        account_index: l?.account_index ?? 0,
        allocated_amount: l?.allocated_amount ?? "",
      })),
    })) as WizardDraft["goals"],
  };
}

export default function Step5BlockerPreview() {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const draft = useWatch({ control: form.control });
  if (draft === undefined) return null;
  const blockers = computeWizardBlockers(normalizeDraft(draft as DraftLike));
  if (blockers.length === 0) return null;

  return (
    <aside
      role="alert"
      aria-labelledby="wizard-blocker-preview-title"
      className="border border-danger bg-paper-2 px-4 py-3"
      data-testid="step5-blocker-preview"
    >
      <p
        id="wizard-blocker-preview-title"
        className="font-mono text-[10px] uppercase tracking-widest text-danger mb-2"
      >
        {t("wizard.step5.blocker_preview.title")}
      </p>
      <ul className="flex flex-col gap-1 list-disc list-inside font-sans text-[12px] text-ink">
        {blockers.map((blocker, idx) => (
          <li key={`${blocker.code}-${idx}`} data-blocker-code={blocker.code}>
            <strong className="font-medium">
              {blocker.account_label ?? blocker.goal_label ?? ""}
            </strong>
            {blocker.account_label !== undefined && " — "}
            {blocker.goal_label !== undefined && blocker.account_label === undefined && " — "}
            {renderBlockerMessage(blocker, t)}
          </li>
        ))}
      </ul>
      <p className="mt-2 font-sans text-[11px] text-muted">
        {t("wizard.step5.blocker_preview.footer")}
      </p>
    </aside>
  );
}

function renderBlockerMessage(
  blocker: PortfolioGenerationBlocker,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  switch (blocker.code) {
    case "purpose_account_unallocated": {
      const unallocatedDollars =
        (blocker.account_unallocated_basis_points ?? 0) / 100;
      const accountValueDollars =
        (blocker.account_value_basis_points ?? 0) / 100;
      return t("wizard.step5.blocker_preview.purpose_account_unallocated", {
        account_value: formatCadCompact(accountValueDollars),
        unallocated: formatCadCompact(unallocatedDollars),
      });
    }
    case "goal_missing_target_amount":
      return t("wizard.step5.blocker_preview.goal_missing_target_amount");
    case "goal_zero_legs":
      return t("wizard.step5.blocker_preview.goal_zero_legs");
    default:
      return t("wizard.step5.blocker_preview.generic", { code: blocker.code });
  }
}
