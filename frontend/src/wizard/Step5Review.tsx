/**
 * Wizard step 5 — read-only review + client-side pre-flight check +
 * commit affordance.
 *
 * Renders the full draft as a visual receipt; the parent route
 * renders the actual Commit button (so it can wire the mutation +
 * navigation). This component is presentation only.
 *
 * Pre-flight check (added this session): client-side spot-check for the
 * most common readiness gap — "each account's leg amounts sum to its
 * total". Surfacing this here lets the advisor fix it BEFORE commit
 * rather than discovering it via the post-commit warning toast. The
 * authoritative readiness check still runs server-side via
 * `portfolio_generation_blockers_for_household`; client-side is a
 * helpful hint, not a gate (advisor can still commit if they choose
 * to address gaps later).
 */
import { useFormContext, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { type WizardDraft } from "./schema";
import { formatCad } from "../lib/format";

interface AccountAllocationIssue {
  index: number;
  account_label: string;
  account_value: number;
  allocated: number;
  missing_holdings: boolean;
}

// Minimal shape of `useWatch` output we read from. react-hook-form
// returns DeepPartial under the hood; using a structural type here
// (rather than Partial<WizardDraft>) avoids the cascade of `string |
// undefined` mismatches without disabling type-safety.
interface PreflightDraft {
  accounts?: Array<
    | {
        account_type?: string;
        current_value?: string;
        missing_holdings_confirmed?: boolean;
      }
    | undefined
  >;
  goals?: Array<
    | {
        legs?: Array<
          | {
              account_index?: number;
              allocated_amount?: string;
            }
          | undefined
        >;
      }
    | undefined
  >;
}

function computePreflightIssues(draft: PreflightDraft): AccountAllocationIssue[] {
  // Pre-flight only checks alignments that are pure-arithmetic +
  // deterministic on the client. The full server-side check covers
  // additional invariants (account_type enum, goal target_date present,
  // etc.). Per canon §9.4.5: never invent semantics — if a check is
  // ambiguous client-side (e.g., depends on Decimal precision), defer
  // to server.
  const accounts = draft.accounts ?? [];
  const goals = draft.goals ?? [];
  const issues: AccountAllocationIssue[] = [];
  for (let i = 0; i < accounts.length; i++) {
    const acct = accounts[i];
    if (!acct) continue;
    const acctValue = Number(acct.current_value ?? "0");
    if (!Number.isFinite(acctValue) || acctValue <= 0) continue;
    let allocated = 0;
    for (const g of goals) {
      for (const leg of g?.legs ?? []) {
        if ((leg?.account_index ?? -1) === i) {
          allocated += Number(leg?.allocated_amount ?? "0") || 0;
        }
      }
    }
    // 1-cent tolerance to absorb floating-point precision (matches the
    // Decimal("1.00") tolerance the server uses).
    const mismatch = Math.abs(allocated - acctValue) > 0.01;
    const missingHoldings = !(acct.missing_holdings_confirmed ?? false);
    if (mismatch || missingHoldings) {
      issues.push({
        index: i,
        account_label: `${acct.account_type ?? "Account"} #${i + 1}`,
        account_value: acctValue,
        allocated,
        missing_holdings: missingHoldings,
      });
    }
  }
  return issues;
}

export function Step5Review() {
  const { t } = useTranslation();
  const form = useFormContext<WizardDraft>();
  const draft = useWatch({ control: form.control });

  if (draft === undefined) return null;

  const preflightIssues = computePreflightIssues(draft);

  return (
    <section
      aria-labelledby="wizard-step5-title"
      className="flex flex-col gap-5 border border-hairline-2 bg-paper p-6 shadow-sm"
    >
      <header>
        <h2
          id="wizard-step5-title"
          className="font-serif text-xl font-medium tracking-tight text-ink"
        >
          {t("wizard.step5.title")}
        </h2>
        <p className="mt-1 text-[12px] text-muted">{t("wizard.step5.subtitle")}</p>
      </header>

      {preflightIssues.length > 0 && (
        <aside
          role="alert"
          aria-labelledby="wizard-preflight-title"
          className="border border-warning bg-paper-2 px-4 py-3"
        >
          <p
            id="wizard-preflight-title"
            className="font-mono text-[10px] uppercase tracking-widest text-warning mb-2"
          >
            {t("wizard.step5.preflight_title")}
          </p>
          <ul className="flex flex-col gap-1 list-disc list-inside font-sans text-[12px] text-ink">
            {preflightIssues.map((issue) => (
              <li key={issue.index}>
                <strong className="font-medium">{issue.account_label}</strong>
                {" — "}
                {Math.abs(issue.allocated - issue.account_value) > 0.01 && (
                  <span>
                    {t("wizard.step5.preflight_allocation_mismatch", {
                      account: formatCad(issue.account_value),
                      allocated: formatCad(issue.allocated),
                    })}
                  </span>
                )}
                {issue.missing_holdings &&
                  Math.abs(issue.allocated - issue.account_value) <= 0.01 && (
                    <span>{t("wizard.step5.preflight_missing_holdings")}</span>
                  )}
                {issue.missing_holdings &&
                  Math.abs(issue.allocated - issue.account_value) > 0.01 && (
                    <span> · {t("wizard.step5.preflight_missing_holdings")}</span>
                  )}
              </li>
            ))}
          </ul>
          <p className="mt-2 font-sans text-[11px] text-muted">
            {t("wizard.step5.preflight_footer")}
          </p>
        </aside>
      )}

      <div className="grid grid-cols-2 gap-5">
        <Section title={t("wizard.step5.identity")}>
          <KeyVal label={t("wizard.step1.name_label")} value={draft.display_name ?? "—"} />
          <KeyVal
            label={t("wizard.step1.type_label")}
            value={
              draft.household_type === "couple"
                ? t("wizard.step1.type_couple")
                : t("wizard.step1.type_single")
            }
          />
          <KeyVal
            label={t("wizard.step5.members")}
            value={(draft.members ?? [])
              .map((m) => `${m?.name ?? "?"} (${m?.dob ?? "—"})`)
              .join(", ")}
          />
          {(draft.notes ?? "").length > 0 && (
            <KeyVal label={t("wizard.step1.notes_label")} value={draft.notes ?? ""} />
          )}
        </Section>

        <Section title={t("wizard.step5.risk_profile")}>
          <KeyVal label="Q1" value={String(draft.risk_profile?.q1 ?? "—")} />
          <KeyVal label="Q2" value={draft.risk_profile?.q2 ?? "—"} />
          <KeyVal label="Q3" value={(draft.risk_profile?.q3 ?? []).join(", ") || "—"} />
          <KeyVal label="Q4" value={draft.risk_profile?.q4 ?? "—"} />
        </Section>

        <Section title={t("wizard.step5.accounts")}>
          {(draft.accounts ?? []).map((account, index) => (
            <KeyVal
              key={index}
              label={`${index + 1}. ${account?.account_type ?? "?"}`}
              value={
                account?.current_value !== undefined && account.current_value !== ""
                  ? formatCad(Number(account.current_value))
                  : "—"
              }
            />
          ))}
        </Section>

        <Section title={t("wizard.step5.goals")}>
          {(draft.goals ?? []).map((goal, gIdx) => (
            <div key={gIdx} className="border-t border-hairline pt-2 first:border-t-0 first:pt-0">
              <p className="font-sans text-[13px] font-medium text-ink">
                {goal?.name ?? "—"}{" "}
                {goal?.target_amount !== undefined && goal.target_amount !== "" && (
                  <span className="font-mono text-[11px] text-accent-2">
                    {formatCad(Number(goal.target_amount))}
                  </span>
                )}
              </p>
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
                {t("wizard.step5.goal_horizon", { date: goal?.target_date ?? "—" })}
              </p>
              <ul className="mt-1 flex flex-col gap-0.5">
                {(goal?.legs ?? []).map((leg, lIdx) => {
                  const idx = leg?.account_index ?? 0;
                  const acct = (draft.accounts ?? [])[idx];
                  return (
                    <li
                      key={lIdx}
                      className="flex items-baseline justify-between font-mono text-[10px]"
                    >
                      <span className="text-muted">{acct?.account_type ?? "?"}</span>
                      <span className="text-ink">
                        {leg?.allocated_amount !== undefined && leg.allocated_amount !== ""
                          ? formatCad(Number(leg.allocated_amount))
                          : "—"}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </Section>

        {(draft.external_holdings ?? []).length > 0 && (
          <Section title={t("wizard.step5.external_holdings")} fullWidth>
            <ul className="flex flex-col gap-1">
              {(draft.external_holdings ?? []).map((row, idx) => (
                <li key={idx} className="flex items-baseline justify-between font-mono text-[11px]">
                  <span className="text-ink">
                    {row?.name !== undefined && row.name.length > 0 ? row.name : `#${idx + 1}`}
                  </span>
                  <span className="text-accent-2">
                    {row?.value !== undefined && row.value !== ""
                      ? formatCad(Number(row.value))
                      : "—"}
                  </span>
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    </section>
  );
}

function Section({
  title,
  children,
  fullWidth = false,
}: {
  title: string;
  children: React.ReactNode;
  fullWidth?: boolean;
}) {
  return (
    <section
      className={
        fullWidth
          ? "col-span-2 border border-hairline bg-paper-2 p-4"
          : "border border-hairline bg-paper-2 p-4"
      }
    >
      <h3 className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted">{title}</h3>
      <div className="flex flex-col gap-1">{children}</div>
    </section>
  );
}

function KeyVal({ label, value }: { label: string; value: string }) {
  return (
    <p className="flex items-baseline justify-between gap-2 font-mono text-[11px]">
      <span className="text-muted">{label}</span>
      <span className="text-right text-ink">{value}</span>
    </p>
  );
}
