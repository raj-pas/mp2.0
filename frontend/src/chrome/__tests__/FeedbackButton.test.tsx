/**
 * FeedbackButton + FeedbackModal unit tests (Phase 6 sub-session #4).
 *
 * Targets the open/close + form-validation surface and the submit
 * payload shape that ops triages from /api/feedback/report/. Mocks
 * `useSubmitFeedback` so no actual fetch fires; mocks `useLocation`
 * so the component can read `pathname` without wrapping in a Router.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FeedbackButton } from "../FeedbackButton";

const submitMutate = vi.fn();
const submitPending = { current: false };

vi.mock("../../lib/auth", () => ({
  useSubmitFeedback: () => ({
    mutate: submitMutate,
    get isPending() {
      return submitPending.current;
    },
  }),
}));

vi.mock("react-router-dom", () => ({
  useLocation: () => ({ pathname: "/console/account/abc" }),
}));

vi.mock("../../lib/toast", () => ({
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

afterEach(() => {
  submitMutate.mockClear();
  submitPending.current = false;
  window.sessionStorage.clear();
});

describe("FeedbackButton", () => {
  it("clicking the button opens the FeedbackModal form", () => {
    render(<FeedbackButton />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.feedback.open_label" }),
    );
    expect(screen.getByRole("dialog")).toHaveAttribute(
      "aria-label",
      "chrome.feedback.modal_label",
    );
    // Description textarea + submit button are visible.
    expect(screen.getByText("chrome.feedback.description_label")).toBeInTheDocument();
  });

  it("renders 3 severity radios (blocking / friction / suggestion)", () => {
    render(<FeedbackButton />);
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.feedback.open_label" }),
    );
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(3);
    const values = radios.map((r) => (r as HTMLInputElement).value);
    expect(values).toEqual(["blocking", "friction", "suggestion"]);
    // Default is 'friction'.
    const friction = radios.find(
      (r) => (r as HTMLInputElement).value === "friction",
    ) as HTMLInputElement;
    expect(friction.checked).toBe(true);
  });

  it("submit stays disabled until description is >= 20 chars", () => {
    render(<FeedbackButton />);
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.feedback.open_label" }),
    );
    const submit = screen.getByRole("button", { name: "chrome.feedback.submit" });
    expect(submit).toBeDisabled();

    const textarea = screen.getByPlaceholderText(
      "chrome.feedback.description_placeholder",
    );
    fireEvent.change(textarea, { target: { value: "too short" } });
    expect(submit).toBeDisabled();

    fireEvent.change(textarea, {
      target: { value: "this description is well above twenty chars" },
    });
    expect(submit).not.toBeDisabled();
  });

  it("submitting calls useSubmitFeedback.mutate with the canonical payload", () => {
    window.sessionStorage.setItem("mp20_session_id", "sess-123");
    render(<FeedbackButton />);
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.feedback.open_label" }),
    );
    fireEvent.change(
      screen.getByPlaceholderText("chrome.feedback.description_placeholder"),
      { target: { value: "treemap legend overlapped after risk slider preview" } },
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /chrome.feedback.severity_blocking/ }),
    );
    fireEvent.click(screen.getByRole("button", { name: "chrome.feedback.submit" }));

    expect(submitMutate).toHaveBeenCalledTimes(1);
    const [payload] = submitMutate.mock.calls[0] ?? [];
    expect(payload).toMatchObject({
      severity: "blocking",
      description: "treemap legend overlapped after risk slider preview",
      route: "/console/account/abc",
      session_id: "sess-123",
    });
  });

  it("clicking Cancel closes the modal without firing a mutation", () => {
    render(<FeedbackButton />);
    fireEvent.click(
      screen.getByRole("button", { name: "chrome.feedback.open_label" }),
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "chrome.feedback.cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(submitMutate).not.toHaveBeenCalled();
  });
});
