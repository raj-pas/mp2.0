/**
 * Zod schema mirroring `WizardCommitSerializer` on the backend.
 *
 * The shape was verified live during the pre-R5 smoke (see
 * docs/agent/handoff-log.md 2026-04-30 — pre-R5 wizard smoke).
 * Keep this file in sync with `web/api/wizard_views.py` —
 * locked decision #29 (react-hook-form + zod) is the only
 * approved client validation surface.
 */
import { z } from "zod";

export const ACCOUNT_TYPES = [
  "RRSP",
  "TFSA",
  "RESP",
  "RDSP",
  "FHSA",
  "Non-Registered",
  "LIRA",
  "RRIF",
  "Corporate",
] as const;

export type AccountType = (typeof ACCOUNT_TYPES)[number];

export const Q2Q4_CHOICES = ["A", "B", "C", "D"] as const;
export type Q2Q4Choice = (typeof Q2Q4_CHOICES)[number];

// Q3 stressors — locked decision #5 vocabulary; mirrors the canon
// stress-trigger taxonomy. Persisted as a list of selected codes.
export const Q3_STRESSORS = ["career", "health", "family", "market_volatility"] as const;
export type Q3Stressor = (typeof Q3_STRESSORS)[number];

const memberSchema = z.object({
  name: z.string().trim().min(1, "Name required."),
  dob: z.string().trim().min(1, "DOB required."),
});

const accountSchema = z.object({
  account_type: z.enum(ACCOUNT_TYPES),
  current_value: z
    .string()
    .trim()
    .refine((s) => /^\d+(\.\d{1,2})?$/.test(s), "Use a number like 120000.00"),
  custodian: z.string().trim().default(""),
  /**
   * Advisor confirms "no fund-level holdings to track" for this account
   * (e.g., GIC, single-fund, cash). When true, engine-readiness accepts
   * the account without holdings; when false (default), the readiness
   * check requires either holdings or this confirmation before
   * portfolio generation can succeed.
   *
   * Per canon §9.4.5 + locked decision (this session): default false so
   * the advisor consciously opts in — never silently mark missing.
   */
  missing_holdings_confirmed: z.boolean().default(false),
});

const goalLegSchema = z.object({
  account_index: z.number().int().nonnegative(),
  allocated_amount: z
    .string()
    .trim()
    .refine((s) => /^\d+(\.\d{1,2})?$/.test(s), "Use a number like 120000.00"),
});

const goalSchema = z.object({
  name: z.string().trim().min(1, "Goal name required."),
  target_date: z.string().trim().min(1, "Target date required."),
  necessity_score: z.number().int().min(1).max(5),
  target_amount: z
    .string()
    .trim()
    .refine((s) => s === "" || /^\d+(\.\d{1,2})?$/.test(s), "Use a number or leave blank.")
    .optional()
    .default(""),
  legs: z.array(goalLegSchema).min(1, "Each goal needs at least one account leg."),
});

const externalHoldingSchema = z
  .object({
    name: z.string().trim().default(""),
    value: z
      .string()
      .trim()
      .refine((s) => /^\d+(\.\d{1,2})?$/.test(s), "Use a number."),
    equity_pct: z.string().trim(),
    fixed_income_pct: z.string().trim(),
    cash_pct: z.string().trim(),
    real_assets_pct: z.string().trim(),
  })
  .superRefine((row, ctx) => {
    const total =
      Number(row.equity_pct) +
      Number(row.fixed_income_pct) +
      Number(row.cash_pct) +
      Number(row.real_assets_pct);
    if (Math.abs(total - 100) > 0.01) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `Asset percentages must sum to 100; got ${total.toFixed(2)}.`,
        path: ["equity_pct"],
      });
    }
  });

/**
 * Account-centric tolerance: legs allocated to a Purpose account must sum
 * to its `current_value` within $0.01 (1 cent — equivalent to the backend
 * `Decimal("1.00")` tolerance applied to dollar amounts in
 * `web/api/review_state.py:380-385`).
 *
 * Locked decision §A1.14 #5: HARD-BLOCK Continue until every Purpose
 * account is fully allocated. Mirrors backend portfolio-readiness gate
 * EXACTLY so wizard commit cannot succeed-then-fail at the engine.
 */
const ACCOUNT_ALLOCATION_TOLERANCE = 0.01;

export const wizardSchema = z
  .object({
    display_name: z.string().trim().min(1, "Household name required."),
    household_type: z.enum(["single", "couple"]),
    joint_consent: z.boolean().default(false),
    members: z.array(memberSchema).min(1).max(2),
    notes: z.string().trim().default(""),
    risk_profile: z.object({
      q1: z.number().int().min(0).max(10),
      q2: z.enum(Q2Q4_CHOICES),
      q3: z.array(z.enum(Q3_STRESSORS)).default([]),
      q4: z.enum(Q2Q4_CHOICES),
    }),
    accounts: z.array(accountSchema).min(1, "Add at least one account."),
    goals: z.array(goalSchema).min(1, "Add at least one goal."),
    external_holdings: z.array(externalHoldingSchema).default([]),
  })
  .superRefine((draft, ctx) => {
    if (draft.household_type === "couple") {
      if (!draft.joint_consent) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Joint consent required for couple households.",
          path: ["joint_consent"],
        });
      }
      if (draft.members.length !== 2) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Couple households need two members.",
          path: ["members"],
        });
      }
    } else if (draft.members.length !== 1) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Single households need one member.",
        path: ["members"],
      });
    }

    // Each leg's account_index must point to a real account.
    draft.goals.forEach((goal, gIdx) => {
      goal.legs.forEach((leg, lIdx) => {
        if (leg.account_index >= draft.accounts.length) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Leg points to an account that hasn't been added yet.",
            path: ["goals", gIdx, "legs", lIdx, "account_index"],
          });
        }
      });
    });

    // ─────────────────────────────────────────────────────────────────
    // Account-centric hard-block (P14 / §A1.14 #5 LOCKED).
    //
    // Wizard accounts default to is_held_at_purpose=True (see
    // web/api/review_state.py:1025), so we apply this gate to ALL
    // wizard-created accounts. Sum of legs.allocated_amount across
    // every goal must equal account.current_value within 1 cent.
    //
    // Edge cases (per §A1.50 P14 row):
    //   - current_value = 0 → trivially passes (sum 0 == 0)
    //   - 1bp value + 1bp leg → passes (within tolerance)
    //   - 1 account / 1 goal → still must satisfy the gate
    //   - non-numeric current_value → skip (the field-level zod
    //     refinement on accountSchema will already flag it; the
    //     account-centric gate would emit a noisy duplicate error)
    // ─────────────────────────────────────────────────────────────────
    draft.accounts.forEach((account, accIdx) => {
      const acctValue = Number(account.current_value);
      if (!Number.isFinite(acctValue)) return;
      let allocated = 0;
      for (const goal of draft.goals) {
        for (const leg of goal.legs) {
          if (leg.account_index === accIdx) {
            const legAmount = Number(leg.allocated_amount);
            if (Number.isFinite(legAmount)) allocated += legAmount;
          }
        }
      }
      if (Math.abs(allocated - acctValue) > ACCOUNT_ALLOCATION_TOLERANCE) {
        const unallocated = acctValue - allocated;
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          // i18n key — translation happens in the surface (Step3Goals).
          // params encode the account label + the unallocated amount so
          // the wizard can render compact CAD without reformatting.
          message: JSON.stringify({
            key: "wizard.step3.account_unallocated",
            params: {
              account_label: `${account.account_type} #${accIdx + 1}`,
              account_value: acctValue,
              allocated,
              unallocated,
            },
          }),
          path: ["accounts", accIdx, "current_value"],
        });
      }
    });

    // ─────────────────────────────────────────────────────────────────
    // Goal-side hard-block (P14 / §A1.14 #16 LOCKED).
    //
    // Every goal must have:
    //   (a) at least one leg with positive allocated_amount, AND
    //   (b) target_amount > 0
    //
    // Mirrors backend portfolio-readiness gate (a goal with zero legs
    // or zero target produces a degenerate optimization input).
    //
    // Edge cases (per §A1.50 P14 row):
    //   - 0 legs → emit at goals.<i>.legs (the zod min(1) on legs
    //     already covers this; we add a redundant guard here so the
    //     hard-block is consistent regardless of legs.length)
    //   - 1 leg allocated_amount = 0 → emit at goals.<i>.legs (no
    //     positive leg means the goal is funded with zero dollars)
    //   - target_amount empty / 0 → emit at goals.<i>.target_amount
    // ─────────────────────────────────────────────────────────────────
    draft.goals.forEach((goal, gIdx) => {
      const hasPositiveLeg = goal.legs.some((leg) => {
        const amount = Number(leg.allocated_amount);
        return Number.isFinite(amount) && amount > 0;
      });
      if (!hasPositiveLeg) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: JSON.stringify({
            key: "wizard.step3.goal_legs_required",
            params: { goal_label: goal.name || `Goal ${gIdx + 1}` },
          }),
          path: ["goals", gIdx, "legs"],
        });
      }
      const targetAmount = Number(goal.target_amount);
      if (
        !goal.target_amount ||
        !Number.isFinite(targetAmount) ||
        targetAmount <= 0
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: JSON.stringify({
            key: "wizard.step3.goal_target_required",
            params: { goal_label: goal.name || `Goal ${gIdx + 1}` },
          }),
          path: ["goals", gIdx, "target_amount"],
        });
      }
    });
  });

export type WizardDraft = z.infer<typeof wizardSchema>;

/**
 * Empty draft used for first-paint and "discard recovery" reset.
 */
export function emptyWizardDraft(): WizardDraft {
  return {
    display_name: "",
    household_type: "single",
    joint_consent: false,
    members: [{ name: "", dob: "" }],
    notes: "",
    risk_profile: { q1: 5, q2: "B", q3: [], q4: "B" },
    accounts: [
      {
        account_type: "RRSP",
        current_value: "",
        custodian: "",
        missing_holdings_confirmed: false,
      },
    ],
    goals: [
      {
        name: "",
        target_date: "",
        necessity_score: 3,
        target_amount: "",
        legs: [{ account_index: 0, allocated_amount: "" }],
      },
    ],
    external_holdings: [],
  };
}

export type CommitPayload = Omit<WizardDraft, "joint_consent">;

export function draftToCommitPayload(draft: WizardDraft): CommitPayload {
  // joint_consent is a frontend-only validation field; the backend
  // doesn't accept it. Strip before POST.
  const { joint_consent: _consent, external_holdings, ...rest } = draft;
  return {
    ...rest,
    external_holdings: external_holdings ?? [],
  };
}
