/**
 * DocDetailPanel unit tests — covers the Phase 5b.5 slide-out:
 * pending skeleton, facts grouped by section, edit + add-fact mutation
 * payload shapes, close (X + Escape). Phase 6 sub-session #4.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocDetailPanel } from "../DocDetailPanel";
import type { ContributedFact, ReviewDocumentDetail } from "../../lib/review";

const useReviewDocumentMock = vi.fn();
const applyMutate = vi.fn();

vi.mock("../../lib/review", () => ({
  useReviewDocument: (workspaceId: string | null, documentId: number | null) =>
    useReviewDocumentMock(workspaceId, documentId),
  useApplyFactOverride: () => ({ mutate: applyMutate, isPending: false }),
}));
vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

const baseFact: ContributedFact = {
  fact_id: 11,
  field: "people[0].date_of_birth",
  label: "Person 0 — DOB",
  section: "people",
  value: "1972-03-14",
  confidence: "high",
  derivation_method: "extracted",
  source_location: "p.2",
  source_page: 2,
  redacted_evidence_quote: "DOB: [REDACTED]",
  asserted_at: "2026-05-01T00:00:00Z",
};

function makeDetail(
  overrides: Partial<ReviewDocumentDetail> = {},
): ReviewDocumentDetail {
  // Cast to ReviewDocumentDetail — only the fields DocDetailPanel reads
  // are populated; the rest of ReviewDocument is unused on this surface.
  return {
    document_id: 100,
    original_filename: "kyc.pdf",
    document_type: "kyc",
    contributed_facts: [
      baseFact,
      {
        ...baseFact,
        fact_id: 12,
        section: "accounts",
        field: "accounts[0].current_value",
        label: "Account 0 — Value",
        value: 50000,
      },
    ],
    ...overrides,
  } as ReviewDocumentDetail;
}

function mockSuccess(detail: ReviewDocumentDetail = makeDetail()) {
  useReviewDocumentMock.mockReturnValue({
    isPending: false,
    isError: false,
    data: detail,
  });
}

afterEach(() => {
  useReviewDocumentMock.mockReset();
  applyMutate.mockClear();
});

describe("DocDetailPanel", () => {
  it("returns null when documentId is null", () => {
    useReviewDocumentMock.mockReturnValue({ isPending: false, isError: false });
    const { container } = render(
      <DocDetailPanel workspaceId="ws-1" documentId={null} onClose={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders skeleton while review document is pending", () => {
    useReviewDocumentMock.mockReturnValue({ isPending: true, isError: false });
    render(<DocDetailPanel workspaceId="ws-1" documentId={100} onClose={() => {}} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("doc_detail.loading")).toBeInTheDocument();
  });

  it("renders facts grouped by section after success", () => {
    mockSuccess();
    render(<DocDetailPanel workspaceId="ws-1" documentId={100} onClose={() => {}} />);
    expect(screen.getByText("kyc.pdf")).toBeInTheDocument();
    // Section headings: the i18n mock returns the `defaultValue` option
    // when it's present, so the heading renders as the bare section name.
    expect(screen.getByText("people")).toBeInTheDocument();
    expect(screen.getByText("accounts")).toBeInTheDocument();
    expect(screen.getByText("Person 0 — DOB")).toBeInTheDocument();
    expect(screen.getByText("Account 0 — Value")).toBeInTheDocument();
  });

  it("clicking the pencil button opens FactEditForm", () => {
    mockSuccess(makeDetail({ contributed_facts: [baseFact] }));
    render(<DocDetailPanel workspaceId="ws-1" documentId={100} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /doc_detail.edit_aria/ }));
    expect(
      screen.getByRole("button", { name: "doc_detail.edit_save" }),
    ).toBeInTheDocument();
  });

  it("saving an edit calls useApplyFactOverride.mutate with is_added=false", () => {
    mockSuccess(makeDetail({ contributed_facts: [baseFact] }));
    render(<DocDetailPanel workspaceId="ws-1" documentId={100} onClose={() => {}} />);
    fireEvent.click(
      screen.getByRole("button", { name: /doc_detail.edit_aria/ }),
    );
    // Edit value (input is pre-filled with formatted current value).
    // Two textboxes inside the edit form: value (input) + rationale (textarea).
    const [valueInput, rationaleInput] = screen.getAllByRole("textbox");
    if (!valueInput || !rationaleInput) {
      throw new Error("expected value + rationale textboxes in the edit form");
    }
    fireEvent.change(valueInput, { target: { value: "1972-03-15" } });
    fireEvent.change(rationaleInput, {
      target: { value: "Corrected per signed KYC" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "doc_detail.edit_save" }),
    );

    expect(applyMutate).toHaveBeenCalledTimes(1);
    const [payload] = applyMutate.mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      field: "people[0].date_of_birth",
      value: "1972-03-15",
      rationale: "Corrected per signed KYC",
      is_added: false,
    });
  });

  it("Add fact CTA opens AddFactSection and saves with is_added=true", () => {
    // No contributed facts → the only textboxes on screen are the
    // AddFactSection's value+rationale (the field input is a combobox
    // due to its datalist binding); keeps selectors simple.
    mockSuccess(makeDetail({ contributed_facts: [] }));
    render(<DocDetailPanel workspaceId="ws-1" documentId={100} onClose={() => {}} />);
    fireEvent.click(
      screen.getByRole("button", { name: "doc_detail.add_action" }),
    );
    expect(
      screen.getByRole("button", { name: "doc_detail.add_save" }),
    ).toBeInTheDocument();

    // Within AddFactSection: field input has `list=` so it gets the
    // ARIA `combobox` role; value input + rationale textarea remain
    // `textbox`. Pluck them by the i18n placeholder text.
    const fieldInput = screen.getByPlaceholderText(
      "doc_detail.add_field_placeholder",
    );
    // value input + rationale textarea (datalist-bound field input is a combobox).
    const [valueInput, rationaleInput] = screen.getAllByRole("textbox");
    if (!valueInput || !rationaleInput) {
      throw new Error("expected value + rationale textboxes in the add form");
    }
    fireEvent.change(fieldInput, {
      target: { value: "people[1].date_of_birth" },
    });
    fireEvent.change(valueInput, { target: { value: "1974-08-21" } });
    fireEvent.change(rationaleInput, {
      target: { value: "Spouse DOB from KYC page 3" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "doc_detail.add_save" }),
    );

    expect(applyMutate).toHaveBeenCalledTimes(1);
    const [payload] = applyMutate.mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      field: "people[1].date_of_birth",
      value: "1974-08-21",
      rationale: "Spouse DOB from KYC page 3",
      is_added: true,
    });
  });

  it("close button calls onClose; Escape key also calls onClose", () => {
    mockSuccess();
    const onClose = vi.fn();
    render(<DocDetailPanel workspaceId="ws-1" documentId={100} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "doc_detail.close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
