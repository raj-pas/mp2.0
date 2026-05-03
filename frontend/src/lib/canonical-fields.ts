/**
 * Canonical-field shape map.
 *
 * Sub-session #10 (Phase R7 Tier 1): drives the inline edit form's
 * input-type selection (date / number / dropdown / text) and the
 * "Add fact" datalist autocomplete.
 *
 * The map is hand-maintained so the FE doesn't need to know about
 * Pydantic field internals at runtime. Each entry mirrors the
 * canonical path as enumerated in `extraction/prompts/base.py`
 * `CANONICAL_FIELD_INVENTORY`. Wildcards (`[N]`) match any positive
 * integer index.
 *
 * Why hand-rolled instead of OpenAPI-generated:
 * - The OpenAPI schema describes wire shapes, not advisor-edit
 *   semantics (e.g. `risk.household_score` is `number` on the wire
 *   but here we encode min=1 / max=5 / step=1 for the input control).
 * - Enum option labels need i18n-friendly display copy, not the raw
 *   enum value the engine consumes.
 * - The list is small (~30 entries); the maintenance burden is
 *   trivial vs. the FE/BE drift class the codegen guard catches.
 */
export type CanonicalFieldKind = "date" | "number" | "enum" | "text";

export interface EnumOption {
  /** Engine-canonical value (lowercase enum), what the BE stores. */
  value: string;
  /** Advisor-facing label (i18n-key would be cleaner; left for v2). */
  label: string;
}

export interface CanonicalFieldShape {
  kind: CanonicalFieldKind;
  enum_options?: EnumOption[];
  min?: number;
  max?: number;
  step?: number;
}

const MARITAL_STATUS_OPTIONS: EnumOption[] = [
  { value: "single", label: "Single" },
  { value: "married", label: "Married" },
  { value: "common_law", label: "Common law" },
  { value: "divorced", label: "Divorced" },
  { value: "widowed", label: "Widowed" },
  { value: "separated", label: "Separated" },
];

const INVESTMENT_KNOWLEDGE_OPTIONS: EnumOption[] = [
  { value: "none", label: "None" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const ACCOUNT_TYPE_OPTIONS: EnumOption[] = [
  { value: "rrsp", label: "RRSP" },
  { value: "tfsa", label: "TFSA" },
  { value: "rrif", label: "RRIF" },
  { value: "non_registered", label: "Non-registered" },
  { value: "resp", label: "RESP" },
  { value: "lira", label: "LIRA" },
  { value: "lrif", label: "LRIF" },
  { value: "other", label: "Other" },
];

const REGULATORY_OBJECTIVE_OPTIONS: EnumOption[] = [
  { value: "safety", label: "Safety" },
  { value: "income", label: "Income" },
  { value: "balanced_income_growth", label: "Balanced income / growth" },
  { value: "growth", label: "Growth" },
  { value: "aggressive_growth", label: "Aggressive growth" },
];

const REGULATORY_TIME_HORIZON_OPTIONS: EnumOption[] = [
  { value: "short", label: "Short (0-3 yrs)" },
  { value: "medium", label: "Medium (3-9 yrs)" },
  { value: "long", label: "Long (9+ yrs)" },
];

const REGULATORY_RISK_RATING_OPTIONS: EnumOption[] = [
  { value: "low", label: "Low" },
  { value: "low_medium", label: "Low-medium" },
  { value: "medium", label: "Medium" },
  { value: "medium_high", label: "Medium-high" },
  { value: "high", label: "High" },
];

const HOUSEHOLD_TYPE_OPTIONS: EnumOption[] = [
  { value: "individual", label: "Individual" },
  { value: "couple", label: "Couple" },
  { value: "family", label: "Family" },
];

const TAX_RESIDENCY_OPTIONS: EnumOption[] = [
  { value: "canada-quebec", label: "Canada — Québec" },
  { value: "canada-non-quebec", label: "Canada — non-Québec" },
  { value: "other", label: "Other" },
];

const PRIORITY_OPTIONS: EnumOption[] = [
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

/**
 * Field-pattern → shape entries. The KEY is a regex source that
 * matches the field-path string at runtime; lookup walks the list
 * in order and returns the first match. Specific patterns first,
 * generic fallbacks last.
 */
const FIELD_SHAPE_PATTERNS: Array<{ pattern: RegExp; shape: CanonicalFieldShape }> = [
  // Date fields
  { pattern: /^people\[\d+\]\.date_of_birth$/, shape: { kind: "date" } },
  { pattern: /\.asserted_at$/, shape: { kind: "date" } },
  { pattern: /\.statement_date$/, shape: { kind: "date" } },

  // Numeric fields with bounds
  {
    pattern: /^risk\.household_score$/,
    shape: { kind: "number", min: 1, max: 5, step: 1 },
  },
  {
    pattern: /^people\[\d+\]\.age$/,
    shape: { kind: "number", min: 0, max: 120, step: 1 },
  },
  {
    pattern: /^goals\[\d+\]\.time_horizon_years$/,
    shape: { kind: "number", min: 0, max: 60, step: 1 },
  },

  // Numeric currency fields
  {
    pattern: /^accounts\[\d+\]\.current_value$/,
    shape: { kind: "number", min: 0, step: 0.01 },
  },
  {
    pattern: /^goals\[\d+\]\.target_amount$/,
    shape: { kind: "number", min: 0, step: 0.01 },
  },
  {
    pattern: /^goal_account_links\[\d+\]\.allocated_amount$/,
    shape: { kind: "number", min: 0, step: 0.01 },
  },

  // Enum fields
  {
    pattern: /^people\[\d+\]\.marital_status$/,
    shape: { kind: "enum", enum_options: MARITAL_STATUS_OPTIONS },
  },
  {
    pattern: /^people\[\d+\]\.investment_knowledge$/,
    shape: { kind: "enum", enum_options: INVESTMENT_KNOWLEDGE_OPTIONS },
  },
  {
    pattern: /^accounts\[\d+\]\.account_type$/,
    shape: { kind: "enum", enum_options: ACCOUNT_TYPE_OPTIONS },
  },
  {
    pattern: /^accounts\[\d+\]\.regulatory_objective$/,
    shape: { kind: "enum", enum_options: REGULATORY_OBJECTIVE_OPTIONS },
  },
  {
    pattern: /^accounts\[\d+\]\.regulatory_time_horizon$/,
    shape: { kind: "enum", enum_options: REGULATORY_TIME_HORIZON_OPTIONS },
  },
  {
    pattern: /^accounts\[\d+\]\.regulatory_risk_rating$/,
    shape: { kind: "enum", enum_options: REGULATORY_RISK_RATING_OPTIONS },
  },
  {
    pattern: /^household\.household_type$/,
    shape: { kind: "enum", enum_options: HOUSEHOLD_TYPE_OPTIONS },
  },
  {
    pattern: /^household\.tax_residency$/,
    shape: { kind: "enum", enum_options: TAX_RESIDENCY_OPTIONS },
  },
  {
    pattern: /^goals\[\d+\]\.priority$/,
    shape: { kind: "enum", enum_options: PRIORITY_OPTIONS },
  },

  // Boolean (rendered as enum)
  {
    pattern: /^accounts\[\d+\]\.missing_holdings_confirmed$/,
    shape: {
      kind: "enum",
      enum_options: [
        { value: "true", label: "Yes" },
        { value: "false", label: "No" },
      ],
    },
  },
];

/**
 * Returns the shape descriptor for a canonical field path. Defaults
 * to ``text`` for paths that don't match any known pattern (custom
 * advisor-defined paths, behavioral_notes.* free-form fields).
 */
export function getCanonicalFieldShape(field_path: string): CanonicalFieldShape {
  for (const entry of FIELD_SHAPE_PATTERNS) {
    if (entry.pattern.test(field_path)) {
      return entry.shape;
    }
  }
  return { kind: "text" };
}

/**
 * Full canonical-field listing for autocomplete (Sub-session #10.2).
 *
 * Wildcard indices use [0] as the canonical first instance; advisor
 * edits the index to whatever is needed. A single household has
 * ~25 canonical fields per person/account/goal so the list scales
 * with N personas.
 */
export const CANONICAL_FIELD_AUTOCOMPLETE: string[] = [
  "household.display_name",
  "household.household_type",
  "household.tax_residency",
  "people[0].display_name",
  "people[0].date_of_birth",
  "people[0].age",
  "people[0].marital_status",
  "people[0].investment_knowledge",
  "people[1].display_name",
  "people[1].date_of_birth",
  "people[1].age",
  "people[1].marital_status",
  "people[1].investment_knowledge",
  "accounts[0].account_type",
  "accounts[0].account_number",
  "accounts[0].current_value",
  "accounts[0].missing_holdings_confirmed",
  "accounts[0].regulatory_objective",
  "accounts[0].regulatory_time_horizon",
  "accounts[0].regulatory_risk_rating",
  "accounts[1].account_type",
  "accounts[1].current_value",
  "accounts[1].regulatory_objective",
  "goals[0].name",
  "goals[0].time_horizon_years",
  "goals[0].target_amount",
  "goals[0].priority",
  "goals[1].name",
  "goals[1].time_horizon_years",
  "goals[1].target_amount",
  "goals[1].priority",
  "goal_account_links[0].goal_name",
  "goal_account_links[0].account_id_or_label",
  "goal_account_links[0].allocated_amount",
  "risk.household_score",
];
