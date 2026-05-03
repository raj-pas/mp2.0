/**
 * Sub-session #10.1 — schema-driven inline edit unit tests for the
 * canonical-fields helper.
 */
import { describe, expect, it } from "vitest";

import {
  CANONICAL_FIELD_AUTOCOMPLETE,
  getCanonicalFieldShape,
} from "../canonical-fields";

describe("getCanonicalFieldShape", () => {
  it("returns date kind for people[N].date_of_birth", () => {
    expect(getCanonicalFieldShape("people[0].date_of_birth").kind).toBe("date");
    expect(getCanonicalFieldShape("people[2].date_of_birth").kind).toBe("date");
  });

  it("returns date kind for any .asserted_at path", () => {
    expect(getCanonicalFieldShape("anything.asserted_at").kind).toBe("date");
  });

  it("returns number kind with bounds for risk.household_score", () => {
    const shape = getCanonicalFieldShape("risk.household_score");
    expect(shape.kind).toBe("number");
    expect(shape.min).toBe(1);
    expect(shape.max).toBe(5);
    expect(shape.step).toBe(1);
  });

  it("returns number kind for accounts[N].current_value", () => {
    const shape = getCanonicalFieldShape("accounts[3].current_value");
    expect(shape.kind).toBe("number");
    expect(shape.min).toBe(0);
    expect(shape.step).toBe(0.01);
  });

  it("returns enum with marital options for marital_status", () => {
    const shape = getCanonicalFieldShape("people[1].marital_status");
    expect(shape.kind).toBe("enum");
    const values = shape.enum_options?.map((option) => option.value);
    expect(values).toEqual([
      "single",
      "married",
      "common_law",
      "divorced",
      "widowed",
      "separated",
    ]);
  });

  it("returns enum with regulatory_objective options", () => {
    const shape = getCanonicalFieldShape("accounts[0].regulatory_objective");
    expect(shape.kind).toBe("enum");
    expect(shape.enum_options?.length).toBe(5);
    expect(shape.enum_options?.[0]?.value).toBe("safety");
  });

  it("returns enum bool options for missing_holdings_confirmed", () => {
    const shape = getCanonicalFieldShape("accounts[0].missing_holdings_confirmed");
    expect(shape.kind).toBe("enum");
    expect(shape.enum_options).toEqual([
      { value: "true", label: "Yes" },
      { value: "false", label: "No" },
    ]);
  });

  it("returns text kind for unknown / behavioral_notes paths", () => {
    expect(getCanonicalFieldShape("household.display_name").kind).toBe("text");
    expect(getCanonicalFieldShape("behavioral_notes.whatever").kind).toBe("text");
    expect(getCanonicalFieldShape("custom.advisor.path").kind).toBe("text");
  });

  it("returns text kind for the goal name field (free-form)", () => {
    expect(getCanonicalFieldShape("goals[0].name").kind).toBe("text");
  });
});

describe("CANONICAL_FIELD_AUTOCOMPLETE", () => {
  it("includes household + people[0/1] + accounts + goals + risk paths", () => {
    expect(CANONICAL_FIELD_AUTOCOMPLETE).toContain("household.display_name");
    expect(CANONICAL_FIELD_AUTOCOMPLETE).toContain("people[0].date_of_birth");
    expect(CANONICAL_FIELD_AUTOCOMPLETE).toContain("people[1].display_name");
    expect(CANONICAL_FIELD_AUTOCOMPLETE).toContain("accounts[0].current_value");
    expect(CANONICAL_FIELD_AUTOCOMPLETE).toContain("goals[0].target_amount");
    expect(CANONICAL_FIELD_AUTOCOMPLETE).toContain("risk.household_score");
  });

  it("contains at least 30 entries to cover the canonical surface", () => {
    expect(CANONICAL_FIELD_AUTOCOMPLETE.length).toBeGreaterThanOrEqual(30);
  });

  it("entries are unique", () => {
    const set = new Set(CANONICAL_FIELD_AUTOCOMPLETE);
    expect(set.size).toBe(CANONICAL_FIELD_AUTOCOMPLETE.length);
  });
});
