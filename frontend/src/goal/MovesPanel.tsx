import { useTranslation } from "react-i18next";

import { Skeleton } from "../components/ui/skeleton";
import { fundColor, fundDisplayName } from "../lib/funds";
import { useMoves } from "../lib/preview";
import { formatCad } from "../lib/format";

interface MovesPanelProps {
  householdId: string;
  goalId: string;
}

export function MovesPanel({ householdId, goalId }: MovesPanelProps) {
  const { t } = useTranslation();
  const query = useMoves(householdId, goalId);

  if (query.isPending) {
    return (
      <Section title={t("moves.section_title")}>
        <Skeleton className="h-24 w-full" />
      </Section>
    );
  }
  if (query.isError || query.data === undefined) {
    return (
      <Section title={t("moves.section_title")}>
        <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
          {t("errors.preview_failed")}
        </p>
      </Section>
    );
  }

  const moves = query.data.moves;
  if (moves.length === 0) {
    return (
      <Section title={t("moves.section_title")}>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("moves.no_moves")}
        </p>
      </Section>
    );
  }

  const buys = moves.filter((m) => m.action === "buy");
  const sells = moves.filter((m) => m.action === "sell");
  const totalBuy = query.data.total_buy ?? buys.reduce((s, m) => s + Number(m.amount), 0);
  const totalSell = query.data.total_sell ?? sells.reduce((s, m) => s + Number(m.amount), 0);

  return (
    <Section title={t("moves.section_title")}>
      <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("moves.totals", { buys: formatCad(totalBuy), sells: formatCad(totalSell) })}
      </p>
      <div className="grid grid-cols-2 gap-4">
        <MoveColumn heading={t("moves.buys")} actionLabel={t("moves.buy_action")} rows={buys} />
        <MoveColumn heading={t("moves.sells")} actionLabel={t("moves.sell_action")} rows={sells} />
      </div>
    </Section>
  );
}

function MoveColumn({
  heading,
  rows,
}: {
  heading: string;
  actionLabel: string;
  rows: { fund_id: string; fund_name: string; amount: number }[];
}) {
  if (rows.length === 0) {
    return (
      <div>
        <p className="mb-2 font-mono text-[9px] uppercase tracking-widest text-muted">{heading}</p>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">—</p>
      </div>
    );
  }
  return (
    <div>
      <p className="mb-2 font-mono text-[9px] uppercase tracking-widest text-muted">{heading}</p>
      <ul className="flex flex-col divide-y divide-hairline">
        {rows.map((row) => (
          <li key={row.fund_id} className="flex items-center gap-2 py-1.5">
            <span
              aria-hidden
              className="inline-block h-2 w-2"
              style={{ background: fundColor(row.fund_id) }}
            />
            <span className="flex-1 truncate font-sans text-[12px] text-ink">
              {fundDisplayName(row.fund_id, row.fund_name)}
            </span>
            <span className="font-mono text-[10px] text-accent-2">
              {formatCad(Number(row.amount))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border border-hairline-2 bg-paper p-4 shadow-sm">
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted">{title}</h3>
      {children}
    </section>
  );
}
