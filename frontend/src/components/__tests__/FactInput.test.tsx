/**
 * FactInput unit tests — Pair 5 (P3.3) shared input dispatcher.
 *
 * Covers each kind branch (date, number, enum, text) plus the
 * focus-on-mount useEffect for both the input + select code paths.
 * The component is small (~80 LoC); these tests get the coverage
 * gate to ≥90% per sister §3.14.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FactInput } from "../FactInput";

describe("FactInput", () => {
  it("renders a date input for `people[0].date_of_birth`", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="people[0].date_of_birth"
        value=""
        onChange={onChange}
      />,
    );
    const input = document.querySelector('input[type="date"]');
    expect(input).not.toBeNull();
  });

  it("renders a number input with min/max for `risk.household_score`", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="risk.household_score"
        value=""
        onChange={onChange}
      />,
    );
    const input = document.querySelector('input[type="number"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.min).toBe("1");
    expect(input.max).toBe("5");
    expect(input.step).toBe("1");
  });

  it("renders an enum <select> with the canonical options for `accounts[0].account_type`", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="accounts[0].account_type"
        value=""
        onChange={onChange}
        selectPlaceholder="Pick…"
      />,
    );
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    // Placeholder option present (disabled).
    expect(screen.getByText("Pick…")).toBeInTheDocument();
    // Canonical RRSP/TFSA options render.
    expect(screen.getByText("RRSP")).toBeInTheDocument();
    expect(screen.getByText("TFSA")).toBeInTheDocument();
  });

  it("falls back to text input for unknown / empty field paths", () => {
    const onChange = vi.fn();
    render(<FactInput fieldPath="" value="" onChange={onChange} />);
    const input = document.querySelector('input[type="text"]');
    expect(input).not.toBeNull();
  });

  it("invokes onChange on input typing", () => {
    const onChange = vi.fn();
    render(
      <FactInput fieldPath="goals[0].name" value="" onChange={onChange} />,
    );
    const input = document.querySelector('input[type="text"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Retirement" } });
    expect(onChange).toHaveBeenCalledWith("Retirement");
  });

  it("invokes onChange on select change for enum fields", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="accounts[0].account_type"
        value=""
        onChange={onChange}
      />,
    );
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "rrsp" } });
    expect(onChange).toHaveBeenCalledWith("rrsp");
  });

  it("focuses the input when focusOnMount is true (text path)", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="goals[0].name"
        value=""
        onChange={onChange}
        focusOnMount
      />,
    );
    const input = document.querySelector('input[type="text"]');
    expect(document.activeElement).toBe(input);
  });

  it("focuses the select when focusOnMount is true (enum path)", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="accounts[0].account_type"
        value=""
        onChange={onChange}
        focusOnMount
      />,
    );
    const select = screen.getByRole("combobox");
    expect(document.activeElement).toBe(select);
  });

  it("respects the disabled prop on text input", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="goals[0].name"
        value=""
        onChange={onChange}
        disabled
      />,
    );
    const input = document.querySelector('input[type="text"]') as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });

  it("respects the disabled prop on select", () => {
    const onChange = vi.fn();
    render(
      <FactInput
        fieldPath="accounts[0].account_type"
        value=""
        onChange={onChange}
        disabled
      />,
    );
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.disabled).toBe(true);
  });
});
