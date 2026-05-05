/**
 * P3.1 (plan v20 §A1.32) — i18n regression guard.
 *
 * Pins en.json so the stale "Phase R<N>" labels from the v36 UX
 * migration plan (R0-R10) cannot leak back into user-visible copy.
 * The canon taxonomy is Phase A/B/C; the internal round labels are
 * implementation-only and never reach advisor/analyst eyes.
 *
 * Companion to scripts/check-vocab.sh — the shell guard catches
 * source files broadly; this Vitest catches the JSON catalog at the
 * unit-test layer so a regression surfaces before the lint step.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
const EN_JSON_PATH = resolve(HERE, "..", "en.json");

describe("i18n en.json — Phase R<N> regression guard", () => {
  it("contains zero 'Phase R<digit>' substrings (canon Phase A/B/C only)", () => {
    const raw = readFileSync(EN_JSON_PATH, "utf-8");
    const matches = raw.match(/Phase R\d/g);
    expect(matches).toBeNull();
  });
});
