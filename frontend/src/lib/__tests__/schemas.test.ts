/**
 * P5 (plan v20 §A1.34) — shared lib/schemas.ts round-trip tests.
 *
 * Closes G7: Wizard and Review previously held divergent zod
 * definitions for Person / Account / Goal / GoalAccountLink. These
 * tests pin the canonical base schemas so a future drift (e.g. a
 * surface adds a non-extending field) fails compile + assertion.
 *
 * Round-trip identity: a wizard-shaped reviewed_state slice should
 * parse cleanly into the canonical base schemas + survive a JSON
 * stringify/parse loop without losing or coercing fields. This is
 * the strongest guarantee that "what the wizard saves" === "what
 * the review surface reads".
 */
import { describe, expect, it } from "vitest";

import {
  BaseAccountSchema,
  BaseGoalAccountLinkSchema,
  BaseGoalSchema,
  BasePersonSchema,
  CANON_ACCOUNT_TYPES,
  CANON_RISK_DESCRIPTORS,
  CANON_RISK_PERCENTILE,
  CANON_RISK_SCORES,
} from "../schemas";

describe("BasePersonSchema round-trip", () => {
  it("parses canonical person input + survives JSON round-trip", () => {
    const input = { name: "Sandra Chen", dob: "1979-05-14" };
    const parsed = BasePersonSchema.parse(input);
    const reparsed = BasePersonSchema.parse(JSON.parse(JSON.stringify(parsed)));
    expect(reparsed).toEqual(input);
  });

  it("rejects empty name + empty dob (mirrors WizardCommitSerializer required fields)", () => {
    expect(() => BasePersonSchema.parse({ name: "", dob: "1979-05-14" })).toThrow();
    expect(() => BasePersonSchema.parse({ name: "Sandra", dob: "" })).toThrow();
  });
});

describe("BaseAccountSchema round-trip", () => {
  it("parses every canon account type", () => {
    for (const type of CANON_ACCOUNT_TYPES) {
      const input = {
        account_type: type,
        current_value: "120000.00",
        custodian: "Steadyhand",
      };
      const parsed = BaseAccountSchema.parse(input);
      expect(parsed.account_type).toBe(type);
      expect(parsed.current_value).toBe("120000.00");
    }
  });

  it("round-trips a typical wizard account through JSON without drift", () => {
    const input = {
      account_type: "RRSP" as const,
      current_value: "450000.00",
      custodian: "Purpose",
    };
    const parsed = BaseAccountSchema.parse(input);
    const reparsed = BaseAccountSchema.parse(JSON.parse(JSON.stringify(parsed)));
    expect(reparsed).toEqual(input);
  });

  it("custodian defaults to empty string when omitted (DRF parity)", () => {
    const parsed = BaseAccountSchema.parse({
      account_type: "TFSA",
      current_value: "10000.00",
    });
    expect(parsed.custodian).toBe("");
  });
});

describe("BaseGoalAccountLinkSchema round-trip", () => {
  it("parses canonical link + survives JSON round-trip", () => {
    const input = { account_index: 0, allocated_amount: "10000.00" };
    const parsed = BaseGoalAccountLinkSchema.parse(input);
    const reparsed = BaseGoalAccountLinkSchema.parse(
      JSON.parse(JSON.stringify(parsed)),
    );
    expect(reparsed).toEqual(input);
  });
});

describe("BaseGoalSchema round-trip", () => {
  it("parses a goal with one leg + non-empty target_amount", () => {
    const input = {
      name: "Retirement",
      target_date: "2046-01-01",
      necessity_score: 4,
      target_amount: "1500000.00",
      legs: [{ account_index: 0, allocated_amount: "450000.00" }],
    };
    const parsed = BaseGoalSchema.parse(input);
    const reparsed = BaseGoalSchema.parse(JSON.parse(JSON.stringify(parsed)));
    expect(reparsed.name).toBe("Retirement");
    expect(reparsed.legs).toHaveLength(1);
    expect(reparsed.target_amount).toBe("1500000.00");
  });

  it("rejects a goal with zero legs (mirrors WizardCommitSerializer min(1))", () => {
    const input = {
      name: "Retirement",
      target_date: "2046-01-01",
      necessity_score: 3,
      target_amount: "1000000.00",
      legs: [] as { account_index: number; allocated_amount: string }[],
    };
    expect(() => BaseGoalSchema.parse(input)).toThrow();
  });
});

describe("wizardSchema consumes lib/schemas via .extend() (P5 refactor)", () => {
  it("wizardSchema accepts a couple household with joint_consent + 2 members", async () => {
    const { wizardSchema } = await import("../../wizard/schema");
    const draft = {
      display_name: "Chen household",
      household_type: "couple" as const,
      joint_consent: true,
      members: [
        { name: "Sandra Chen", dob: "1979-05-14" },
        { name: "Mike Chen", dob: "1977-09-02" },
      ],
      notes: "",
      risk_profile: { q1: 5, q2: "B" as const, q3: [], q4: "B" as const },
      accounts: [
        {
          account_type: "RRSP" as const,
          current_value: "100000.00",
          custodian: "Steadyhand",
          missing_holdings_confirmed: false,
        },
      ],
      goals: [
        {
          name: "Retirement",
          target_date: "2046-01-01",
          necessity_score: 4,
          target_amount: "1000000.00",
          legs: [{ account_index: 0, allocated_amount: "100000.00" }],
        },
      ],
      external_holdings: [],
    };
    const parsed = wizardSchema.parse(draft);
    expect(parsed.members).toHaveLength(2);
    expect(parsed.accounts[0]?.missing_holdings_confirmed).toBe(false);
  });

  it("wizardSchema flags external_holdings rows whose asset percentages don't sum to 100", async () => {
    const { wizardSchema } = await import("../../wizard/schema");
    const draft = {
      display_name: "Solo household",
      household_type: "single" as const,
      joint_consent: false,
      members: [{ name: "Solo", dob: "1980-01-01" }],
      notes: "",
      risk_profile: { q1: 5, q2: "B" as const, q3: [], q4: "B" as const },
      accounts: [
        {
          account_type: "RRSP" as const,
          current_value: "100000.00",
          custodian: "",
          missing_holdings_confirmed: false,
        },
      ],
      goals: [
        {
          name: "Retirement",
          target_date: "2046-01-01",
          necessity_score: 4,
          target_amount: "1000000.00",
          legs: [{ account_index: 0, allocated_amount: "100000.00" }],
        },
      ],
      external_holdings: [
        {
          name: "Outside RRSP",
          value: "50000.00",
          equity_pct: "50",
          fixed_income_pct: "20",
          cash_pct: "10",
          real_assets_pct: "5", // sums to 85, not 100
        },
      ],
    };
    const result = wizardSchema.safeParse(draft);
    expect(result.success).toBe(false);
    if (!result.success) {
      const messages = result.error.issues.map((issue) => issue.message);
      expect(
        messages.some((m) => /Asset percentages must sum to 100/.test(m)),
      ).toBe(true);
    }
  });

  it("wizardSchema rejects a couple household without joint_consent (superRefine)", async () => {
    const { wizardSchema } = await import("../../wizard/schema");
    const draft = {
      display_name: "Chen household",
      household_type: "couple" as const,
      joint_consent: false,
      members: [
        { name: "Sandra Chen", dob: "1979-05-14" },
        { name: "Mike Chen", dob: "1977-09-02" },
      ],
      notes: "",
      risk_profile: { q1: 5, q2: "B" as const, q3: [], q4: "B" as const },
      accounts: [
        {
          account_type: "RRSP" as const,
          current_value: "100000.00",
          custodian: "",
          missing_holdings_confirmed: false,
        },
      ],
      goals: [
        {
          name: "Retirement",
          target_date: "2046-01-01",
          necessity_score: 4,
          target_amount: "1000000.00",
          legs: [{ account_index: 0, allocated_amount: "100000.00" }],
        },
      ],
      external_holdings: [],
    };
    const result = wizardSchema.safeParse(draft);
    expect(result.success).toBe(false);
    if (!result.success) {
      const messages = result.error.issues.map((issue) => issue.message);
      expect(messages).toContain("Joint consent required for couple households.");
    }
  });
});

describe("Canon risk constants (canon §11.4)", () => {
  it("CANON_RISK_SCORES enumerates exactly 1..5", () => {
    expect([...CANON_RISK_SCORES]).toEqual([1, 2, 3, 4, 5]);
  });

  it("CANON_RISK_DESCRIPTORS maps 1..5 to canon vocabulary verbatim", () => {
    expect(CANON_RISK_DESCRIPTORS).toEqual({
      1: "Cautious",
      2: "Conservative-balanced",
      3: "Balanced",
      4: "Balanced-growth",
      5: "Growth-oriented",
    });
  });

  it("CANON_RISK_PERCENTILE matches engine BUCKET_REPRESENTATIVE_SCORE 5/15/25/35/45", () => {
    expect(CANON_RISK_PERCENTILE).toEqual({
      1: 5,
      2: 15,
      3: 25,
      4: 35,
      5: 45,
    });
  });
});
