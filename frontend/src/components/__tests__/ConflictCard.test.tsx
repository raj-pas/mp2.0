/**
 * ConflictCard unit tests — covers per-field same-class conflict
 * resolution: radio render, submit gating, resolve+defer mutations,
 * resolved-state body. Phase 6 sub-session #4.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConflictCard } from "../../modals/ConflictPanel";
import type { ConflictCandidate, ReviewConflict } from "../../lib/review";

const resolveMutate = vi.fn();
const deferMutate = vi.fn();

vi.mock("../../lib/review", () => ({
  useResolveConflict: () => ({ mutate: resolveMutate, isPending: false }),
  useDeferConflict: () => ({ mutate: deferMutate, isPending: false }),
}));
vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

const baseCandidate: ConflictCandidate = {
  fact_id: 1,
  value: "Sandra Chen",
  confidence: "high",
  derivation_method: "extracted",
  source_document_id: 100,
  source_document_filename: "kyc.pdf",
  source_document_type: "kyc",
  source_location: "p.1",
  source_page: 1,
  redacted_evidence_quote: "Name: [REDACTED]",
  asserted_at: "2026-05-01T00:00:00Z",
};

function makeConflict(overrides: Partial<ReviewConflict> = {}): ReviewConflict {
  return {
    field: "people[0].full_name",
    label: "Person 0 — Full name",
    section: "people",
    values: ["Sandra Chen", "S. Chen"],
    count: 2,
    fact_ids: [1, 2],
    resolved: false,
    required: true,
    same_authority: false,
    source_types: ["kyc", "statement"],
    candidates: [
      { ...baseCandidate, fact_id: 1 },
      {
        ...baseCandidate,
        fact_id: 2,
        value: "S. Chen",
        source_document_filename: "stmt.pdf",
        source_document_type: "statement",
        confidence: "medium",
      },
    ],
    ...overrides,
  };
}

afterEach(() => {
  resolveMutate.mockClear();
  deferMutate.mockClear();
});

describe("ConflictCard", () => {
  it("renders one radio per candidate", () => {
    render(<ConflictCard workspaceId="ws-1" conflict={makeConflict()} />);
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(2);
    expect(screen.getByText("Sandra Chen")).toBeInTheDocument();
    expect(screen.getByText("S. Chen")).toBeInTheDocument();
  });

  it("submit stays disabled until chosen + rationale + evidence_ack", () => {
    render(<ConflictCard workspaceId="ws-1" conflict={makeConflict()} />);
    const submit = screen.getByRole("button", { name: "review.conflict.submit" });
    expect(submit).toBeDisabled();

    // Pick a candidate.
    const [firstRadio] = screen.getAllByRole("radio");
    if (!firstRadio) throw new Error("expected at least one radio");
    fireEvent.click(firstRadio);
    expect(submit).toBeDisabled();

    // Add rationale.
    const textarea = screen.getByPlaceholderText(
      "review.conflict.rationale_placeholder",
    );
    fireEvent.change(textarea, { target: { value: "KYC supersedes statement" } });
    expect(submit).toBeDisabled();

    // Tick evidence_ack.
    const [firstCheckbox] = screen.getAllByRole("checkbox");
    if (!firstCheckbox) throw new Error("expected at least one checkbox");
    fireEvent.click(firstCheckbox);
    expect(submit).not.toBeDisabled();
  });

  it("submit calls useResolveConflict.mutate with canonical payload", () => {
    render(<ConflictCard workspaceId="ws-1" conflict={makeConflict()} />);
    const radios = screen.getAllByRole("radio");
    const secondRadio = radios[1];
    if (!secondRadio) throw new Error("expected two candidate radios");
    fireEvent.click(secondRadio); // pick fact_id=2
    fireEvent.change(
      screen.getByPlaceholderText("review.conflict.rationale_placeholder"),
      { target: { value: "Statement is most recent." } },
    );
    const [evidenceCheckbox] = screen.getAllByRole("checkbox");
    if (!evidenceCheckbox) throw new Error("expected evidence_ack checkbox");
    fireEvent.click(evidenceCheckbox);
    fireEvent.click(screen.getByRole("button", { name: "review.conflict.submit" }));

    expect(resolveMutate).toHaveBeenCalledTimes(1);
    const [payload] = resolveMutate.mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      field: "people[0].full_name",
      chosen_fact_id: 2,
      rationale: "Statement is most recent.",
      evidence_ack: true,
    });
  });

  it("Decide later toggles the defer form", () => {
    render(<ConflictCard workspaceId="ws-1" conflict={makeConflict()} />);
    expect(
      screen.queryByPlaceholderText("review.conflict.defer_rationale_placeholder"),
    ).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "review.conflict.defer_action" }),
    );
    expect(
      screen.getByPlaceholderText("review.conflict.defer_rationale_placeholder"),
    ).toBeInTheDocument();
  });

  it("Defer save calls useDeferConflict.mutate with field + rationale", () => {
    render(<ConflictCard workspaceId="ws-1" conflict={makeConflict()} />);
    fireEvent.click(
      screen.getByRole("button", { name: "review.conflict.defer_action" }),
    );
    const deferTextarea = screen.getByPlaceholderText(
      "review.conflict.defer_rationale_placeholder",
    );
    const saveBtn = screen.getByRole("button", {
      name: "review.conflict.defer_save",
    });
    expect(saveBtn).toBeDisabled();

    fireEvent.change(deferTextarea, {
      target: { value: "Need fresh KYC from advisor." },
    });
    expect(saveBtn).not.toBeDisabled();
    fireEvent.click(saveBtn);

    expect(deferMutate).toHaveBeenCalledTimes(1);
    const [payload] = deferMutate.mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      field: "people[0].full_name",
      rationale: "Need fresh KYC from advisor.",
    });
  });

  it("renders resolved body without a submit form when resolved", () => {
    render(
      <ConflictCard
        workspaceId="ws-1"
        conflict={makeConflict({
          resolved: true,
          chosen_fact_id: 1,
          resolution: "Sandra Chen",
          rationale: "KYC trumps statement",
          resolved_by: "advisor@example.com",
        })}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "review.conflict.submit" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Sandra Chen")).toBeInTheDocument();
    expect(screen.getByText("KYC trumps statement")).toBeInTheDocument();
    expect(screen.getByText("advisor@example.com")).toBeInTheDocument();
  });
});
