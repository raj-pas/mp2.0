import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "../lib/api";
import { CLIENTS_QUERY_KEY } from "../lib/clients";
import { type CommitPayload } from "./schema";

export type WizardCommitResponse = {
  household_id: string;
  household_score_1_5: 1 | 2 | 3 | 4 | 5;
  /**
   * Server-computed list of advisor-actionable blockers preventing
   * portfolio generation on the just-committed household. Empty list
   * means engine-ready and the auto-trigger likely created a
   * PortfolioRun. Non-empty means commit succeeded but the household
   * needs further advisor attention before recommendations can be
   * generated.
   *
   * Mirrors `HouseholdDetail.readiness_blockers` per locked decision
   * (this session). Frontend onSubmit handler converts a non-empty
   * list into a warning toast (instead of plain success) so the
   * advisor knows to follow up.
   */
  readiness_blockers: string[];
};

/**
 * POST `/api/households/wizard/` — fires `household_wizard_committed`
 * AuditEvent on the server (locked decision #37). On success the
 * client list cache is invalidated so the picker picks up the new
 * household; the new id is also returned for the caller to remember.
 */
export function useWizardCommit() {
  const queryClient = useQueryClient();
  return useMutation<WizardCommitResponse, Error, CommitPayload>({
    mutationFn: (payload) =>
      apiFetch<WizardCommitResponse>("/api/households/wizard/", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CLIENTS_QUERY_KEY });
    },
  });
}
