/**
 * Tier 3 polish coverage — format helpers (§1.4 + §1.10).
 */
import { describe, expect, it } from "vitest";

import {
  formatCad,
  formatCadCompact,
  formatCurrencyCAD,
  formatDateLong,
  formatPct,
} from "../format";

describe("formatCurrencyCAD", () => {
  it("renders en-CA currency with $ prefix and thousands separators", () => {
    expect(formatCurrencyCAD(1234567)).toMatch(/^\$1,234,567/);
  });

  it("returns em-dash for null/undefined/NaN", () => {
    expect(formatCurrencyCAD(null)).toBe("—");
    expect(formatCurrencyCAD(undefined)).toBe("—");
    expect(formatCurrencyCAD(Number.NaN)).toBe("—");
  });

  it("aliases formatCad (same behavior)", () => {
    expect(formatCurrencyCAD(42)).toBe(formatCad(42));
  });
});

describe("formatCadCompact", () => {
  it("compacts large values with K / M suffix", () => {
    const value = formatCadCompact(1_900_000);
    // en-CA compact: "$1.9M" / "$1,9M" depending on locale data.
    // Just assert digits + currency are present.
    expect(value).toMatch(/^\$[\d.,]+/);
    expect(value.length).toBeLessThan("$1,900,000".length);
  });

  it("returns em-dash for null/undefined", () => {
    expect(formatCadCompact(null)).toBe("—");
    expect(formatCadCompact(undefined)).toBe("—");
  });
});

describe("formatPct", () => {
  it("formats 1-digit percent by default", () => {
    expect(formatPct(12.345)).toBe("12.3%");
  });

  it("respects custom digit count", () => {
    expect(formatPct(0.5, 2)).toBe("0.50%");
  });

  it("multiplies by 100 when requested", () => {
    expect(formatPct(0.123, 1, { multiply100: true })).toBe("12.3%");
  });

  it("returns em-dash for null/undefined", () => {
    expect(formatPct(null)).toBe("—");
  });
});

describe("formatDateLong", () => {
  it("renders en-CA long-form date for an ISO string", () => {
    const value = formatDateLong("2026-05-03");
    // en-CA long: "May 3, 2026"
    expect(value).toMatch(/2026/);
    expect(value).toMatch(/May/i);
  });

  it("accepts a Date instance", () => {
    const value = formatDateLong(new Date("2026-05-03"));
    expect(value).toMatch(/2026/);
  });

  it("returns em-dash for null/undefined", () => {
    expect(formatDateLong(null)).toBe("—");
    expect(formatDateLong(undefined)).toBe("—");
  });

  it("returns em-dash for invalid input", () => {
    expect(formatDateLong("not-a-date")).toBe("—");
  });
});
