/**
 * Step5Review + Step5BlockerPreview coverage (P14 §A1.51 P11×P14 LOCKED).
 *
 * Cross-phase contract: the structured `PortfolioGenerationBlocker`
 * shape rendered in Step5BlockerPreview MUST match P11's backend
 * `PortfolioGenerationBlocker` TypedDict byte-for-byte. Advisor sees
 * the SAME copy in the wizard pre-commit preview as on HouseholdRoute
 * post-commit (§A1.27 + §A1.29 invariants).
 *
 * §A1.51 P11×P14 row test ID:
 *   `test_pre_commit_blocker_preview_matches_p11_backend_shape_byte_for_byte`
 */
import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { useForm, FormProvider } from "react-hook-form";

import {
  computeWizardBlockers,
  type PortfolioGenerationBlocker,
} from "../Step5BlockerPreview";
import { Step5Review } from "../Step5Review";
import { type WizardDraft, emptyWizardDraft } from "../schema";

function Harness({ draft }: { draft: WizardDraft }) {
  const form = useForm<WizardDraft>({ defaultValues: draft, mode: "onChange" });
  return (
    <FormProvider {...form}>
      <Step5Review />
    </FormProvider>
  );
}

function makeDraft(overrides: Partial<WizardDraft> = {}): WizardDraft {
  return {
    ...emptyWizardDraft(),
    display_name: "Cross-phase Test Household",
    members: [{ name: "M", dob: "1980-01-01" }],
    accounts: [
      {
        account_type: "RRSP",
        current_value: "900000",
        custodian: "Steadyhand",
        missing_holdings_confirmed: false,
      },
    ],
    goals: [
      {
        name: "YOLO",
        target_date: "2050-01-01",
        necessity_score: 4,
        target_amount: "500000",
        legs: [{ account_index: 0, allocated_amount: "10000" }],
      },
    ],
    ...overrides,
  };
}

describe("Step5BlockerPreview — computeWizardBlockers shape", () => {
  it("test_pre_commit_blocker_preview_matches_p11_backend_shape_byte_for_byte", () => {
    // Cross-phase contract (§A1.51 P11×P14): the rendered structured
    // blockers MUST match P11's `web/api/types.py` TypedDict shape:
    //   {
    //     code: <Literal>,
    //     account_id?: str,
    //     account_label?: str,
    //     account_value_basis_points?: int,
    //     account_unallocated_basis_points?: int,
    //     goal_id?: str,
    //     goal_label?: str,
    //     ui_action: <Literal>,
    //   }
    // We assert byte-for-byte equality against an expected static JSON
    // emitted from the wizard's repro of the Eren Mikasa scenario
    // ($900K Purpose RRSP; $10K assigned to YOLO; $890K unallocated).
    const blockers = computeWizardBlockers(makeDraft());
    const expected: PortfolioGenerationBlocker[] = [
      {
        code: "purpose_account_unallocated",
        account_id: "wizard_account_0",
        account_label: "RRSP #1",
        // basis-points encoding (§A1.27 §line 2793-2794): integer × 100
        account_value_basis_points: 90_000_000,
        account_unallocated_basis_points: 89_000_000,
        ui_action: "assign_to_goal",
      },
    ];
    expect(blockers).toEqual(expected);
  });

  it("emits both account-centric and goal-side blockers when both invariants fail", () => {
    const blockers = computeWizardBlockers(
      makeDraft({
        goals: [
          {
            name: "YOLO",
            target_date: "2050-01-01",
            necessity_score: 4,
            target_amount: "",
            legs: [{ account_index: 0, allocated_amount: "0" }],
          },
        ],
      }),
    );
    // Both account-centric (sum 0 ≠ 900K) AND goal-side (no positive
    // leg + no target_amount) trigger; cross-validation runs both
    // gates without short-circuit (matches schema.test.ts contract).
    expect(blockers.map((b) => b.code).sort()).toEqual(
      [
        "goal_missing_target_amount",
        "goal_zero_legs",
        "purpose_account_unallocated",
      ].sort(),
    );
  });

  it("returns empty list when household is fully allocated and goal-side gates pass", () => {
    const blockers = computeWizardBlockers(
      makeDraft({
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
      }),
    );
    expect(blockers).toEqual([]);
  });
});

describe("Step5Review — lazy-loaded blocker preview render integration", () => {
  it("renders the lazy-loaded preview when blockers exist", async () => {
    render(<Harness draft={makeDraft()} />);
    // The lazy-loaded chunk resolves async; findByTestId waits.
    const preview = await screen.findByTestId("step5-blocker-preview");
    expect(preview).toBeInTheDocument();
  });

  it("renders external_holdings section when present", async () => {
    const draft = makeDraft({
      external_holdings: [
        {
          name: "Old broker",
          value: "50000",
          equity_pct: "60",
          fixed_income_pct: "30",
          cash_pct: "5",
          real_assets_pct: "5",
        },
      ],
      // Fully allocate to avoid spurious blockers in this render path.
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
    });
    render(<Harness draft={draft} />);
    expect(await screen.findByText("Old broker")).toBeInTheDocument();
  });

  it("renders headline + member list (Section + KeyVal helpers)", () => {
    const draft = makeDraft({
      household_type: "couple",
      joint_consent: true,
      members: [
        { name: "Alex", dob: "1980-01-01" },
        { name: "Sam", dob: "1982-02-02" },
      ],
      notes: "Pilot test couple",
    });
    render(<Harness draft={draft} />);
    expect(screen.getByText(/Cross-phase Test Household/)).toBeInTheDocument();
    expect(screen.getByText(/Alex/)).toBeInTheDocument();
    expect(screen.getByText(/Sam/)).toBeInTheDocument();
  });
});
