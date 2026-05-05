/**
 * AllocationBars — P6 (plan v20 §A1.35 / G8) unit tests for the
 * fund-vs-asset-class `mode` prop.
 *
 * Coverage (3 cases):
 *   1. fund mode (default) renders rows verbatim.
 *   2. asset_class mode aggregates via fund metadata
 *      (`aggregateByAssetClass` in lib/format.ts).
 *   3. asset_class mode with unmapped funds surfaces the low-confidence
 *      chip + still renders aggregated rows.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AllocationBars, type AllocationRow } from "../AllocationBars";

function makeRow(overrides: Partial<AllocationRow>): AllocationRow {
  return {
    id: "sh_equity",
    label: "SH Equity",
    pct: 0.5,
    color: "#2E4A6B",
    ...overrides,
  };
}

describe("AllocationBars — fund-vs-asset-class mode (P6)", () => {
  it("fund mode renders the input rows verbatim with their labels", () => {
    const rows: AllocationRow[] = [
      makeRow({ id: "sh_equity", label: "SH Equity", pct: 0.6 }),
      makeRow({ id: "sh_income", label: "SH Income", pct: 0.4 }),
    ];
    render(<AllocationBars rows={rows} mode="fund" ariaLabel="Top funds" />);
    const list = screen.getByRole("list", { name: "Top funds" });
    expect(list).toBeInTheDocument();
    expect(screen.getByText("SH Equity")).toBeInTheDocument();
    expect(screen.getByText("SH Income")).toBeInTheDocument();
    // No low-confidence chip in fund mode.
    expect(
      screen.queryByTestId("allocation-bars-low-confidence"),
    ).not.toBeInTheDocument();
  });

  it("asset_class mode aggregates rows by asset class via fund metadata", () => {
    const rows: AllocationRow[] = [
      // SH-Eq → 100% equity
      makeRow({ id: "sh_equity", label: "SH Equity", pct: 0.6 }),
      // SH-Sav → 100% cash
      makeRow({ id: "sh_savings", label: "SH Savings", pct: 0.4 }),
    ];
    render(<AllocationBars rows={rows} mode="asset_class" ariaLabel="Top asset classes" />);
    // Aggregated labels render — Equity (60%) + Cash (40%).
    expect(screen.getByText("Equity")).toBeInTheDocument();
    expect(screen.getByText("Cash")).toBeInTheDocument();
    // Original fund labels must NOT appear in asset_class mode.
    expect(screen.queryByText("SH Equity")).not.toBeInTheDocument();
    // Both rows mapped → no low-confidence chip.
    expect(
      screen.queryByTestId("allocation-bars-low-confidence"),
    ).not.toBeInTheDocument();
  });

  it("asset_class mode with unmapped fund surfaces the low-confidence chip", () => {
    const rows: AllocationRow[] = [
      makeRow({ id: "sh_equity", label: "SH Equity", pct: 0.6 }),
      // Fabricated fund-id outside the canon universe — aggregation
      // can't resolve it, so it falls through to the lowConfidence path.
      makeRow({ id: "external_unknown_fund", label: "External Fund", pct: 0.4 }),
    ];
    render(<AllocationBars rows={rows} mode="asset_class" ariaLabel="Top asset classes" />);
    expect(
      screen.getByTestId("allocation-bars-low-confidence"),
    ).toBeInTheDocument();
    // Equity bucket still renders (60%); the unmapped 40% surfaces as
    // the synthetic "Unclassified" row.
    expect(screen.getByText("Equity")).toBeInTheDocument();
    expect(screen.getByText("Unclassified")).toBeInTheDocument();
  });
});
