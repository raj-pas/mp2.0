/**
 * Shared zod base schemas + canonical-field constants.
 *
 * P5 / G7 fix (plan v20 §A1.34): Wizard and Review previously held
 * separate definitions of `Person`, `Account`, `Goal`,
 * `GoalAccountLink`, the canon risk descriptors, and the account-type
 * vocabulary. Drift across those two surfaces was a confirmed pilot
 * gap. This module is the single source of truth: surface-specific
 * schemas (e.g. `wizardSchema` in `frontend/src/wizard/schema.ts`)
 * `.extend()` from these bases, never redefine.
 *
 * Field shapes mirror DRF on the backend:
 *   - `web/api/serializers.py` PersonSerializer / AccountSerializer /
 *     GoalSerializer / GoalAccountLinkSerializer
 *   - `web/api/wizard_views.py` WizardCommitSerializer
 *
 * The reviewed-state shape (committed JSON returned by
 * `/api/review/state/`) carries the same canonical-field tree; the
 * shared schemas here are loose where the wire is loose (e.g.
 * `current_value` arrives as a number on reviewed-state but as a
 * string on the wizard-commit payload — `BaseAccountSchema` accepts
 * both via the union and lets surfaces tighten with `.extend()`).
 *
 * Canon §11.4 risk vocabulary lives here too: the descriptor map +
 * 1-5 ↔ percentile mapping (5/15/25/35/45). Surfaces that need to
 * render the descriptor strings consume `lib/risk.ts` (which in turn
 * pulls from this module's constants).
 */
import { z } from "zod";

// ──────────────────────────────────────────────────────────────────
// Canon risk descriptors (§11.4) — locked vocabulary.
//
// Score 1-5 ↔ canon descriptor:
//   1 → Cautious
//   2 → Conservative-balanced
//   3 → Balanced
//   4 → Balanced-growth
//   5 → Growth-oriented
//
// The mockup's retired labels (low / medium / high; bare "Conservative";
// "Aggressive") are explicitly NOT used. Vocab CI
// (`scripts/check-vocab.sh`) blocks regressions.
// ──────────────────────────────────────────────────────────────────
export const CANON_RISK_SCORES = [1, 2, 3, 4, 5] as const;
export type CanonRiskScore = (typeof CANON_RISK_SCORES)[number];

export const CANON_RISK_DESCRIPTORS: Record<CanonRiskScore, string> = {
  1: "Cautious",
  2: "Conservative-balanced",
  3: "Balanced",
  4: "Balanced-growth",
  5: "Growth-oriented",
};

// 1-5 → percentile on the active frontier (canon §11.4 + engine
// `BUCKET_REPRESENTATIVE_SCORE` in `engine/projections.py:60`).
export const CANON_RISK_PERCENTILE: Record<CanonRiskScore, number> = {
  1: 5,
  2: 15,
  3: 25,
  4: 35,
  5: 45,
};

// ──────────────────────────────────────────────────────────────────
// Canonical account types (mirrors `wizard_views.py` ACCOUNT_TYPES +
// `serializers.py` Account.account_type choices).
// ──────────────────────────────────────────────────────────────────
export const CANON_ACCOUNT_TYPES = [
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
export type CanonAccountType = (typeof CANON_ACCOUNT_TYPES)[number];

// ──────────────────────────────────────────────────────────────────
// Money string — wizard-commit payloads serialize Decimal as the
// string form `"120000.00"`. Reviewed-state JSON also uses string
// where Decimal precision matters. Surfaces that read numeric values
// (e.g. ReviewScreen `summarizeReviewedState`) coerce on read.
// ──────────────────────────────────────────────────────────────────
export const moneyStringSchema = z
  .string()
  .trim()
  .refine((s) => /^\d+(\.\d{1,2})?$/.test(s), "Use a number like 120000.00");

// Optional money — accepts empty string + valid money form.
export const optionalMoneyStringSchema = z
  .string()
  .trim()
  .refine((s) => s === "" || /^\d+(\.\d{1,2})?$/.test(s), "Use a number or leave blank.");

// ──────────────────────────────────────────────────────────────────
// Base canonical schemas. Surfaces extend with surface-specific
// flags (e.g. wizard's `missing_holdings_confirmed`) using
// `.extend()`.
// ──────────────────────────────────────────────────────────────────

/** Person — mirrors PersonSerializer + WizardCommitSerializer member. */
export const BasePersonSchema = z.object({
  name: z.string().trim().min(1, "Name required."),
  dob: z.string().trim().min(1, "DOB required."),
});
export type BasePerson = z.infer<typeof BasePersonSchema>;

/** Account — mirrors AccountSerializer + WizardCommitSerializer account. */
export const BaseAccountSchema = z.object({
  account_type: z.enum(CANON_ACCOUNT_TYPES),
  current_value: moneyStringSchema,
  custodian: z.string().trim().default(""),
});
export type BaseAccount = z.infer<typeof BaseAccountSchema>;

/** Goal-account link — mirrors GoalAccountLinkSerializer. */
export const BaseGoalAccountLinkSchema = z.object({
  account_index: z.number().int().nonnegative(),
  allocated_amount: moneyStringSchema,
});
export type BaseGoalAccountLink = z.infer<typeof BaseGoalAccountLinkSchema>;

/** Goal — mirrors GoalSerializer + WizardCommitSerializer goal. */
export const BaseGoalSchema = z.object({
  name: z.string().trim().min(1, "Goal name required."),
  target_date: z.string().trim().min(1, "Target date required."),
  necessity_score: z.number().int().min(1).max(5),
  target_amount: optionalMoneyStringSchema.optional().default(""),
  legs: z.array(BaseGoalAccountLinkSchema).min(1, "Each goal needs at least one account leg."),
});
export type BaseGoal = z.infer<typeof BaseGoalSchema>;
