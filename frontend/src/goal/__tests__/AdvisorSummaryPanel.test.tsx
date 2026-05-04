/**
 * AdvisorSummaryPanel — engine→UI display A3.5 unit tests (sub-session #4 R1).
 *
 * Covers:
 *   - returns null when no link_recommendations match goalId
 *   - 1 section for single-link goal
 *   - N sections for multi-link goal (separator on idx > 0)
 *   - account_type + formatCadCompact in section header
 *   - advisor_summary text rendered verbatim
 *   - aria-labelledby section heading link (locked #109 stays scoped to the
 *     panel; the parent route owns the live region)
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AdvisorSummaryPanel } from "../AdvisorSummaryPanel";
import {
  mockEngineOutput,
  mockHousehold,
  mockLinkRecommendation,
  mockPortfolioRun,
} from "../../__tests__/__fixtures__/household";

describe("AdvisorSummaryPanel", () => {
  it("renders nothing when no link_recommendations match goalId", () => {
    const hh = mockHousehold();
    const { container } = render(
      <AdvisorSummaryPanel household={hh} goalId="goal_does_not_exist" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when latest_portfolio_run is null", () => {
    const hh = mockHousehold({ latest_portfolio_run: null });
    const { container } = render(
      <AdvisorSummaryPanel household={hh} goalId="goal_emma_education" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders 1 section for a single-link goal", () => {
    const hh = mockHousehold();
    render(
      <AdvisorSummaryPanel household={hh} goalId="goal_emma_education" />,
    );
    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(screen.getByText(/Emma education in Non-Registered/)).toBeInTheDocument();
  });

  it("section is wired to its heading via aria-labelledby", () => {
    const hh = mockHousehold();
    render(
      <AdvisorSummaryPanel household={hh} goalId="goal_emma_education" />,
    );
    const region = screen.getByRole("region");
    expect(region).toHaveAttribute(
      "aria-labelledby",
      "advisor-summary-goal_emma_education",
    );
    const heading = screen.getByRole("heading", { level: 3 });
    expect(heading).toHaveAttribute("id", "advisor-summary-goal_emma_education");
  });

  it("renders account_type + formatted CAD amount in section header", () => {
    const hh = mockHousehold();
    render(
      <AdvisorSummaryPanel household={hh} goalId="goal_emma_education" />,
    );
    // Per default fixture: account_type "Non-Registered" + 68000 CAD compact.
    // The header is the <p> directly preceding the advisor_summary <p>; assert
    // via the exact "{type} · {compact}" shape (formatCadCompact uses en-CA
    // compact notation, e.g., "$68K" or "$68.00K" depending on ICU data).
    const header = screen.getByText(/^Non-Registered\s+·\s+\$/);
    expect(header).toBeInTheDocument();
  });

  it("renders the advisor_summary text verbatim", () => {
    const hh = mockHousehold();
    render(
      <AdvisorSummaryPanel household={hh} goalId="goal_emma_education" />,
    );
    expect(
      screen.getByText(
        /Emma education in Non-Registered uses goal risk 1\/5 over 1\.3 years/,
      ),
    ).toBeInTheDocument();
  });

  it("renders one section per LinkRecommendation for multi-link goals", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          link_recommendations: [
            mockLinkRecommendation({
              link_id: "link_1",
              goal_id: "goal_retirement",
              account_id: "acct_mike_rrsp",
              account_type: "RRSP",
              allocated_amount: 620000,
              advisor_summary: "Retirement income — Mike RRSP allocation summary.",
            }),
            mockLinkRecommendation({
              link_id: "link_2",
              goal_id: "goal_retirement",
              account_id: "acct_sandra_rrsp",
              account_type: "RRSP",
              allocated_amount: 430000,
              advisor_summary: "Retirement income — Sandra RRSP allocation summary.",
            }),
            mockLinkRecommendation({
              link_id: "link_3",
              goal_id: "goal_retirement",
              account_id: "acct_joint_tfsa",
              account_type: "TFSA",
              allocated_amount: 70000,
              advisor_summary: "Retirement income — Joint TFSA allocation summary.",
            }),
          ],
        }),
      }),
    });

    render(<AdvisorSummaryPanel household={hh} goalId="goal_retirement" />);
    expect(
      screen.getByText(/Mike RRSP allocation summary/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Sandra RRSP allocation summary/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Joint TFSA allocation summary/),
    ).toBeInTheDocument();
  });

  it("uses link_id as the React key (no duplicate key warnings even for same account_type)", () => {
    const hh = mockHousehold({
      latest_portfolio_run: mockPortfolioRun({
        output: mockEngineOutput({
          link_recommendations: [
            mockLinkRecommendation({
              link_id: "uuid-aaa",
              goal_id: "goal_retirement",
              account_type: "RRSP",
              advisor_summary: "Account A summary.",
            }),
            mockLinkRecommendation({
              link_id: "uuid-bbb",
              goal_id: "goal_retirement",
              account_type: "RRSP",
              advisor_summary: "Account B summary.",
            }),
          ],
        }),
      }),
    });
    render(<AdvisorSummaryPanel household={hh} goalId="goal_retirement" />);
    expect(screen.getByText(/Account A summary/)).toBeInTheDocument();
    expect(screen.getByText(/Account B summary/)).toBeInTheDocument();
  });

  it("renders the panel title heading", () => {
    const hh = mockHousehold();
    render(
      <AdvisorSummaryPanel household={hh} goalId="goal_emma_education" />,
    );
    // i18n stub: t() returns the key
    expect(
      screen.getByRole("heading", { level: 3, name: "goal.advisor_summary_title" }),
    ).toBeInTheDocument();
  });
});
