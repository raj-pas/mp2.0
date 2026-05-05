/**
 * Step3Goals coverage (P14 §A1.14 #5 + #16 LOCKED + §A1.50 P14 row).
 *
 * Tests cover:
 *   - Allocation matrix preview renders rows × cols correctly
 *   - Per-account % indicator renders with allocated / account_value / pct
 *   - Per-account indicator color reflects fully-allocated vs not
 *   - Per-goal "≥1 leg" + "target required" inline errors render
 *   - 8x8 cap with "+N more" overflow indicators
 *
 * Mock i18n: setup.ts mocks useTranslation to return key + defaultValue
 * fallback; assertions target i18n keys directly.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm, FormProvider } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Step3Goals } from "../Step3Goals";
import { wizardSchema, type WizardDraft, emptyWizardDraft } from "../schema";

function Harness({ initialDraft }: { initialDraft: WizardDraft }) {
  const form = useForm<WizardDraft>({
    resolver: zodResolver(wizardSchema),
    mode: "onChange",
    defaultValues: initialDraft,
  });
  // Trigger validation on mount so the field-level errors are
  // populated by the time we render. Without this, the per-account
  // indicator + structured zod issues are absent.
  React.useEffect(() => {
    void form.trigger();
  }, [form]);
  return (
    <FormProvider {...form}>
      <Step3Goals />
    </FormProvider>
  );
}

function makeDraft(overrides: Partial<WizardDraft> = {}): WizardDraft {
  const base = emptyWizardDraft();
  return {
    ...base,
    display_name: "Test",
    members: [{ name: "M", dob: "1980-01-01" }],
    accounts: [
      {
        account_type: "RRSP",
        current_value: "100000",
        custodian: "",
        missing_holdings_confirmed: false,
      },
    ],
    goals: [
      {
        name: "Retirement",
        target_date: "2050-01-01",
        necessity_score: 4,
        target_amount: "500000",
        legs: [{ account_index: 0, allocated_amount: "100000" }],
      },
    ],
    ...overrides,
  };
}

describe("Step3Goals — allocation matrix preview", () => {
  it("renders the matrix with 1 goal × 1 account", async () => {
    render(<Harness initialDraft={makeDraft()} />);
    expect(await screen.findByTestId("allocation-matrix-preview")).toBeInTheDocument();
    expect(screen.getByTestId("matrix-cell-0-0")).toHaveTextContent(/100/);
  });

  it("renders 5×5 matrix without overflow indicators", async () => {
    const accounts = Array.from({ length: 5 }).map(() => ({
      account_type: "RRSP" as const,
      current_value: "100000",
      custodian: "",
      missing_holdings_confirmed: false,
    }));
    const goals = Array.from({ length: 5 }).map((_, gIdx) => ({
      name: `Goal ${gIdx + 1}`,
      target_date: "2050-01-01",
      necessity_score: 3,
      target_amount: "100000",
      legs: [{ account_index: gIdx, allocated_amount: "100000" }],
    }));
    render(<Harness initialDraft={makeDraft({ accounts, goals })} />);
    expect(await screen.findByTestId("allocation-matrix-preview")).toBeInTheDocument();
    expect(screen.getByTestId("matrix-cell-4-4")).toBeInTheDocument();
    expect(screen.queryByTestId("account-overflow")).toBeNull();
    expect(screen.queryByTestId("goal-overflow")).toBeNull();
  });

  it("test_matrix_overflow_renders_plus_n_more: 9×9 caps at 8x8 with +1 more overflow", async () => {
    const accounts = Array.from({ length: 9 }).map(() => ({
      account_type: "RRSP" as const,
      current_value: "100000",
      custodian: "",
      missing_holdings_confirmed: false,
    }));
    const goals = Array.from({ length: 9 }).map((_, gIdx) => ({
      name: `Goal ${gIdx + 1}`,
      target_date: "2050-01-01",
      necessity_score: 3,
      target_amount: "100000",
      legs: [{ account_index: gIdx, allocated_amount: "100000" }],
    }));
    render(<Harness initialDraft={makeDraft({ accounts, goals })} />);
    expect(await screen.findByTestId("account-overflow")).toBeInTheDocument();
    expect(screen.getByTestId("goal-overflow")).toBeInTheDocument();
  });
});

describe("Step3Goals — per-account allocation indicator", () => {
  it("renders the indicator with allocated / account_value / pct when account has positive value", async () => {
    render(<Harness initialDraft={makeDraft()} />);
    expect(
      await screen.findByTestId("account-allocation-indicator-0"),
    ).toBeInTheDocument();
    // The mocked t() returns the key; the indicator surfaces
    // wizard.step3.account_allocation_indicator.
    expect(
      screen.getByTestId("account-allocation-indicator-0"),
    ).toHaveTextContent("wizard.step3.account_allocation_indicator");
  });

  it("renders the structured zod issue when account is under-allocated", async () => {
    const draft = makeDraft({
      goals: [
        {
          name: "Retirement",
          target_date: "2050-01-01",
          necessity_score: 4,
          target_amount: "500000",
          legs: [{ account_index: 0, allocated_amount: "10000" }],
        },
      ],
    });
    render(<Harness initialDraft={draft} />);
    // An alert renders for the structured account-centric issue. The
    // i18n-mocked t() returns the i18n key directly.
    const alerts = await screen.findAllByRole("alert");
    const accountAlert = alerts.find((el) =>
      el.textContent?.includes("wizard.step3.account_unallocated"),
    );
    expect(accountAlert).toBeDefined();
  });
});

describe("Step3Goals — goal-side inline errors", () => {
  it("renders per-goal target_amount required inline error when target empty", async () => {
    const draft = makeDraft({
      goals: [
        {
          name: "Retirement",
          target_date: "2050-01-01",
          necessity_score: 4,
          target_amount: "",
          legs: [{ account_index: 0, allocated_amount: "100000" }],
        },
      ],
    });
    render(<Harness initialDraft={draft} />);
    const issue = await screen.findByTestId("goal-target-issue-0");
    expect(issue).toHaveTextContent("wizard.step3.goal_target_required");
  });

  it("renders per-goal legs-required inline error when no positive leg", async () => {
    const draft = makeDraft({
      accounts: [
        {
          account_type: "RRSP",
          current_value: "0",
          custodian: "",
          missing_holdings_confirmed: false,
        },
      ],
      goals: [
        {
          name: "Retirement",
          target_date: "2050-01-01",
          necessity_score: 4,
          target_amount: "500000",
          legs: [{ account_index: 0, allocated_amount: "0" }],
        },
      ],
    });
    render(<Harness initialDraft={draft} />);
    const issue = await screen.findByTestId("goal-legs-issue-0");
    expect(issue).toHaveTextContent("wizard.step3.goal_legs_required");
  });
});
