/**
 * P5 (plan v20 §A1.34) — risk-helper parity tests.
 *
 * Closes G7: Wizard preview + Review summary previously held
 * separate risk-derivation paths. The shared `descriptorFor` +
 * `scoreToPercentile` helpers in `lib/risk.ts` are now the single
 * source of truth.
 *
 * Identical-output assertion: a Wizard-shaped score (1-5) and a
 * Review-shaped score (read off `reviewed_state.risk.household_score`,
 * which is the same `number` type on the wire) MUST flow through the
 * same helper to produce the same descriptor + percentile. We
 * exercise both call shapes here to pin parity.
 */
import type { TFunction } from "i18next";
import { describe, expect, it } from "vitest";

import {
  descriptorFor,
  isCanonRisk,
  RISK_DESCRIPTOR_KEYS,
  scoreToPercentile,
} from "../risk";

// Identity i18n stub: returns the i18n KEY untouched so assertions
// inspect the canonical key without coupling to en.json. Cast keeps
// the production helper's TFunction signature happy without pulling
// in a full i18next mock.
const tIdentity = ((key: string) => key) as unknown as TFunction;

describe("scoreToPercentile (canon §11.4 1-5 → 5/15/25/35/45)", () => {
  it("maps every canon score to the canon-locked percentile", () => {
    expect(scoreToPercentile(1)).toBe(5);
    expect(scoreToPercentile(2)).toBe(15);
    expect(scoreToPercentile(3)).toBe(25);
    expect(scoreToPercentile(4)).toBe(35);
    expect(scoreToPercentile(5)).toBe(45);
  });

  it("returns null for null + non-canon input (parity with descriptorFor)", () => {
    expect(scoreToPercentile(null)).toBeNull();
    expect(scoreToPercentile(undefined)).toBeNull();
    expect(scoreToPercentile(0)).toBeNull();
    expect(scoreToPercentile(6)).toBeNull();
    expect(scoreToPercentile(2.5)).toBeNull();
  });

  it("Wizard-shape (number) and Review-shape (number) yield identical output", () => {
    // Wizard preview reads `score_1_5` off the server response;
    // Review summary reads `risk.household_score` off reviewed_state.
    // Both arrive as `number`. Identical helper input → identical
    // helper output is the parity invariant we lock here.
    const wizardScore: number = 3;
    const reviewScore: number = 3;
    expect(scoreToPercentile(wizardScore)).toBe(scoreToPercentile(reviewScore));
    expect(scoreToPercentile(wizardScore)).toBe(25);
  });
});

describe("descriptorFor (canon §11.4 descriptor map)", () => {
  it("returns the i18n key for every canon score", () => {
    for (const score of [1, 2, 3, 4, 5] as const) {
      expect(descriptorFor(score, tIdentity)).toBe(RISK_DESCRIPTOR_KEYS[score]);
    }
  });

  it("returns null for null + non-canon input", () => {
    expect(descriptorFor(null, tIdentity)).toBeNull();
    expect(descriptorFor(undefined, tIdentity)).toBeNull();
    expect(descriptorFor(0, tIdentity)).toBeNull();
    expect(descriptorFor(6, tIdentity)).toBeNull();
  });

  it("Wizard-shape and Review-shape inputs resolve to the same descriptor key", () => {
    const wizardScore: number = 4;
    const reviewScore: number = 4;
    expect(descriptorFor(wizardScore, tIdentity)).toBe(
      descriptorFor(reviewScore, tIdentity),
    );
    expect(descriptorFor(wizardScore, tIdentity)).toBe("risk_descriptors.4");
  });
});

describe("isCanonRisk type guard", () => {
  it("accepts 1..5 only; rejects null/undefined/0/6/non-integer", () => {
    expect(isCanonRisk(1)).toBe(true);
    expect(isCanonRisk(5)).toBe(true);
    expect(isCanonRisk(0)).toBe(false);
    expect(isCanonRisk(6)).toBe(false);
    expect(isCanonRisk(null)).toBe(false);
    expect(isCanonRisk(undefined)).toBe(false);
    expect(isCanonRisk(2.5)).toBe(false);
  });
});
