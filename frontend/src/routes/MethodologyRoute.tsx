/**
 * MethodologyRoute — R8 of the v36 UI/UX rewrite (canon §4 + master plan
 * Phase R8). Static reference page that lets advisors trace every score,
 * bucket, projection, and recommendation back to its formula and worked
 * example. Important for compliance/training and advisor trust.
 *
 * Architecture:
 *  - Left TOC (10 sections, anchor links + scrollIntoView)
 *  - Right main content panel (sections render top-to-bottom)
 *  - All section copy + variable labels + worked examples flow through
 *    `t()` (i18n discipline per locked decision #12 + #28a)
 *
 * Vocabulary discipline (locked decisions #5 + #14):
 *  - Client-facing risk descriptors are canon-aligned: Cautious /
 *    Conservative-balanced / Balanced / Balanced-growth / Growth-oriented.
 *  - The retired mockup labels (Conservative / Cautious / Balanced /
 *    Balanced Growth / Growth) are NEVER used.
 *  - Building-block fund (not "sleeve" in product/UX). Re-goaling, never
 *    reallocation.
 *
 * Goal_50 discipline (locked decision #6):
 *  - Goal_50 is purely an internal engine intermediate; never displayed
 *    as a headline number to advisors. Section 3 explains the formula in
 *    canon-1-5 terms; the 0-50 number appears only in a footnote
 *    annotated for engineers reading the methodology.
 *
 * Worked-example numbers come from the v36 mockup methodology (lines
 * 7478–7682, the Hayes/Choi/Thompson illustrative examples). These
 * personas are NOT loaded as fixtures (locked decision #8 retired them);
 * the numbers are quoted as illustrative reference only, with canon
 * vocab updates.
 */
import { useTranslation } from "react-i18next";

import { cn } from "../lib/cn";

interface SectionDef {
  id: string;
  number: number;
  titleKey: string;
}

const SECTIONS: SectionDef[] = [
  { id: "household-risk-profile", number: 1, titleKey: "methodology.s1.title" },
  { id: "anchor", number: 2, titleKey: "methodology.s2.title" },
  { id: "goal-level-risk-score", number: 3, titleKey: "methodology.s3.title" },
  { id: "horizon-cap", number: 4, titleKey: "methodology.s4.title" },
  { id: "effective-bucket", number: 5, titleKey: "methodology.s5.title" },
  { id: "sleeve-mix", number: 6, titleKey: "methodology.s6.title" },
  { id: "projections", number: 7, titleKey: "methodology.s7.title" },
  { id: "rebalancing-moves", number: 8, titleKey: "methodology.s8.title" },
  { id: "realignment", number: 9, titleKey: "methodology.s9.title" },
  { id: "archive-snapshots", number: 10, titleKey: "methodology.s10.title" },
];

export function MethodologyRoute() {
  const { t } = useTranslation();

  function scrollToSection(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <main className="flex flex-1 overflow-hidden bg-paper">
      {/* Left TOC */}
      <aside
        className="flex w-72 shrink-0 flex-col gap-1 overflow-y-auto border-r border-hairline-2 bg-paper-2 p-6"
        aria-label={t("methodology.toc_aria")}
      >
        <h2 className="mb-3 font-serif text-2xl font-medium tracking-tight text-ink">
          {t("methodology.heading")}
        </h2>
        <p className="mb-4 font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("methodology.toc_label")}
        </p>
        <ol className="flex flex-col gap-1">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <button
                type="button"
                onClick={() => scrollToSection(section.id)}
                className="flex w-full items-baseline gap-2 px-2 py-1.5 text-left font-sans text-[12px] text-ink transition-colors hover:bg-paper hover:text-accent-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <span className="font-mono text-[10px] tabular-nums text-muted">
                  {section.number.toString().padStart(2, "0")}
                </span>
                <span>{t(section.titleKey)}</span>
              </button>
            </li>
          ))}
        </ol>
      </aside>

      {/* Right content */}
      <div className="flex-1 overflow-y-auto px-10 py-8">
        <div className="mx-auto max-w-3xl">
          <header className="mb-10">
            <h1 className="font-serif text-3xl font-medium tracking-tight text-ink">
              {t("methodology.heading")}
            </h1>
            <p className="mt-3 text-[13px] leading-relaxed text-muted">
              {t("methodology.intro")}
            </p>
          </header>

          <Section1HouseholdRiskProfile />
          <Section2Anchor />
          <Section3GoalLevelRiskScore />
          <Section4HorizonCap />
          <Section5EffectiveBucket />
          <Section6SleeveMix />
          <Section7Projections />
          <Section8RebalancingMoves />
          <Section9Realignment />
          <Section10ArchiveSnapshots />

          <footer className="mt-16 border-t border-hairline pt-6">
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("methodology.footer")}
            </p>
          </footer>
        </div>
      </div>
    </main>
  );
}

// --- Section primitives -----------------------------------------------

function SectionShell({
  id,
  number,
  titleKey,
  children,
}: {
  id: string;
  number: number;
  titleKey: string;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <section id={id} className="mb-12 scroll-mt-6">
      <header className="mb-4 flex items-baseline gap-3 border-b border-hairline pb-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("methodology.section_marker", { number: number.toString().padStart(2, "0") })}
        </span>
        <h2 className="font-serif text-xl font-medium tracking-tight text-ink">
          {t(titleKey)}
        </h2>
      </header>
      <div className="flex flex-col gap-4 text-[13px] leading-relaxed text-ink">{children}</div>
    </section>
  );
}

function Formula({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <pre
      className={cn(
        "border border-hairline bg-paper-2 px-4 py-3 font-mono text-[12px] leading-relaxed text-ink",
        className,
      )}
    >
      {children}
    </pre>
  );
}

function VariablesTable({ rows }: { rows: { symbol: string; meaning: string }[] }) {
  const { t } = useTranslation();
  return (
    <div className="border border-hairline">
      <table className="w-full border-collapse text-[12px]">
        <thead>
          <tr className="border-b border-hairline bg-paper-2">
            <th className="w-32 px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("methodology.variables_symbol")}
            </th>
            <th className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-muted">
              {t("methodology.variables_meaning")}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.symbol} className="border-t border-hairline">
              <td className="px-3 py-2 font-mono text-[12px] text-ink">{row.symbol}</td>
              <td className="px-3 py-2 font-sans text-[12px] text-ink">{row.meaning}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WorkedExample({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  return (
    <aside className="border-l-2 border-accent bg-paper-2 px-4 py-3">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("methodology.worked_example_label")}
      </p>
      <div className="text-[13px] leading-relaxed text-ink">{children}</div>
    </aside>
  );
}

function Footnote({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  return (
    <p className="text-[11px] italic leading-relaxed text-muted">
      <span className="font-mono uppercase not-italic tracking-widest">
        {t("methodology.footnote_label")}:
      </span>{" "}
      {children}
    </p>
  );
}

// --- Section content --------------------------------------------------

function Section1HouseholdRiskProfile() {
  const { t } = useTranslation();
  return (
    <SectionShell id="household-risk-profile" number={1} titleKey="methodology.s1.title">
      <p>{t("methodology.s1.summary")}</p>
      <Formula>{t("methodology.s1.formula")}</Formula>
      <VariablesTable
        rows={[
          { symbol: "Q1", meaning: t("methodology.s1.var_q1") },
          { symbol: "Q2", meaning: t("methodology.s1.var_q2") },
          { symbol: "Q3", meaning: t("methodology.s1.var_q3") },
          { symbol: "Q4", meaning: t("methodology.s1.var_q4") },
          { symbol: "T", meaning: t("methodology.s1.var_t") },
          { symbol: "C", meaning: t("methodology.s1.var_c") },
        ]}
      />
      <WorkedExample>
        <p>{t("methodology.s1.worked")}</p>
      </WorkedExample>
      <Footnote>{t("methodology.s1.footnote")}</Footnote>
    </SectionShell>
  );
}

function Section2Anchor() {
  const { t } = useTranslation();
  return (
    <SectionShell id="anchor" number={2} titleKey="methodology.s2.title">
      <p>{t("methodology.s2.summary")}</p>
      <Formula>{t("methodology.s2.formula")}</Formula>
      <WorkedExample>
        <p>{t("methodology.s2.worked")}</p>
      </WorkedExample>
    </SectionShell>
  );
}

function Section3GoalLevelRiskScore() {
  const { t } = useTranslation();
  return (
    <SectionShell id="goal-level-risk-score" number={3} titleKey="methodology.s3.title">
      <p>{t("methodology.s3.summary")}</p>
      <Formula>{t("methodology.s3.formula")}</Formula>
      <VariablesTable
        rows={[
          { symbol: "tier", meaning: t("methodology.s3.var_tier") },
          { symbol: "imp_shift", meaning: t("methodology.s3.var_imp_shift") },
          { symbol: "size_shift", meaning: t("methodology.s3.var_size_shift") },
          { symbol: "bucket", meaning: t("methodology.s3.var_bucket") },
        ]}
      />
      <WorkedExample>
        <p>{t("methodology.s3.worked")}</p>
      </WorkedExample>
      <Footnote>{t("methodology.s3.footnote")}</Footnote>
    </SectionShell>
  );
}

function Section4HorizonCap() {
  const { t } = useTranslation();
  return (
    <SectionShell id="horizon-cap" number={4} titleKey="methodology.s4.title">
      <p>{t("methodology.s4.summary")}</p>
      <div className="border border-hairline">
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="border-b border-hairline bg-paper-2">
              <th className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-muted">
                {t("methodology.s4.col_horizon")}
              </th>
              <th className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-muted">
                {t("methodology.s4.col_max_descriptor")}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-hairline">
              <td className="px-3 py-2">{t("methodology.s4.row_under_3")}</td>
              <td className="px-3 py-2">{t("descriptor.cautious")}</td>
            </tr>
            <tr className="border-t border-hairline">
              <td className="px-3 py-2">{t("methodology.s4.row_3_to_5")}</td>
              <td className="px-3 py-2">{t("descriptor.conservative_balanced")}</td>
            </tr>
            <tr className="border-t border-hairline">
              <td className="px-3 py-2">{t("methodology.s4.row_6_to_10")}</td>
              <td className="px-3 py-2">{t("descriptor.balanced")}</td>
            </tr>
            <tr className="border-t border-hairline">
              <td className="px-3 py-2">{t("methodology.s4.row_11_to_20")}</td>
              <td className="px-3 py-2">{t("descriptor.balanced_growth")}</td>
            </tr>
            <tr className="border-t border-hairline">
              <td className="px-3 py-2">{t("methodology.s4.row_over_20")}</td>
              <td className="px-3 py-2">{t("descriptor.growth_oriented")}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </SectionShell>
  );
}

function Section5EffectiveBucket() {
  const { t } = useTranslation();
  return (
    <SectionShell id="effective-bucket" number={5} titleKey="methodology.s5.title">
      <p>{t("methodology.s5.summary")}</p>
      <Formula>{t("methodology.s5.formula")}</Formula>
      <p>{t("methodology.s5.detail")}</p>
    </SectionShell>
  );
}

function Section6SleeveMix() {
  const { t } = useTranslation();
  return (
    <SectionShell id="sleeve-mix" number={6} titleKey="methodology.s6.title">
      <p>{t("methodology.s6.summary")}</p>
      <Formula>{t("methodology.s6.formula")}</Formula>
      <WorkedExample>
        <p>{t("methodology.s6.worked")}</p>
      </WorkedExample>
      <Footnote>{t("methodology.s6.footnote")}</Footnote>
    </SectionShell>
  );
}

function Section7Projections() {
  const { t } = useTranslation();
  return (
    <SectionShell id="projections" number={7} titleKey="methodology.s7.title">
      <p>{t("methodology.s7.summary")}</p>
      <Formula>{t("methodology.s7.formula")}</Formula>
      <p>{t("methodology.s7.detail")}</p>
      <WorkedExample>
        <p>{t("methodology.s7.worked")}</p>
      </WorkedExample>
      <Footnote>{t("methodology.s7.footnote")}</Footnote>
    </SectionShell>
  );
}

function Section8RebalancingMoves() {
  const { t } = useTranslation();
  return (
    <SectionShell id="rebalancing-moves" number={8} titleKey="methodology.s8.title">
      <p>{t("methodology.s8.summary")}</p>
      <Formula>{t("methodology.s8.formula")}</Formula>
      <WorkedExample>
        <p>{t("methodology.s8.worked")}</p>
      </WorkedExample>
    </SectionShell>
  );
}

function Section9Realignment() {
  const { t } = useTranslation();
  return (
    <SectionShell id="realignment" number={9} titleKey="methodology.s9.title">
      <p>{t("methodology.s9.summary")}</p>
      <p>{t("methodology.s9.detail")}</p>
      <Footnote>{t("methodology.s9.footnote")}</Footnote>
    </SectionShell>
  );
}

function Section10ArchiveSnapshots() {
  const { t } = useTranslation();
  return (
    <SectionShell id="archive-snapshots" number={10} titleKey="methodology.s10.title">
      <p>{t("methodology.s10.summary")}</p>
      <VariablesTable
        rows={[
          { symbol: t("methodology.s10.trigger_realignment"), meaning: t("methodology.s10.trigger_realignment_desc") },
          { symbol: t("methodology.s10.trigger_cash_in"), meaning: t("methodology.s10.trigger_cash_in_desc") },
          { symbol: t("methodology.s10.trigger_cash_out"), meaning: t("methodology.s10.trigger_cash_out_desc") },
          { symbol: t("methodology.s10.trigger_re_link"), meaning: t("methodology.s10.trigger_re_link_desc") },
          { symbol: t("methodology.s10.trigger_override"), meaning: t("methodology.s10.trigger_override_desc") },
          { symbol: t("methodology.s10.trigger_re_goal"), meaning: t("methodology.s10.trigger_re_goal_desc") },
          { symbol: t("methodology.s10.trigger_restore"), meaning: t("methodology.s10.trigger_restore_desc") },
        ]}
      />
      <Footnote>{t("methodology.s10.footnote")}</Footnote>
    </SectionShell>
  );
}
