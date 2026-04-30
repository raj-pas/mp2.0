import { ArcElement, Chart as ChartJS, type ChartOptions, Legend, Tooltip } from "chart.js";
import { useEffect, useMemo, useRef } from "react";

import { formatPct } from "../lib/format";

ChartJS.register(ArcElement, Tooltip, Legend);

export type RingDatum = {
  label: string;
  value: number;
  color: string;
};

interface RingChartProps {
  data: RingDatum[];
  ariaLabel: string;
  /** Center label (e.g. "AUM"). */
  centerLabel?: string;
  /** Center value (e.g. "$1.92M"). */
  centerValue?: string;
}

/**
 * Donut chart used for asset-class and geographic exposure rings on
 * AccountRoute and GoalRoute portfolio-stats panels.
 *
 * Rendered with a transparent border + paper-2 cutout to read clean
 * against the v36 paper background (locked decision #5).
 */
export function RingChart({ data, ariaLabel, centerLabel, centerValue }: RingChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<ChartJS<"doughnut"> | null>(null);

  const total = useMemo(() => data.reduce((s, d) => s + d.value, 0), [data]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) return;
    const options: ChartOptions<"doughnut"> = {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const v = Number(ctx.parsed) || 0;
              const pct = total > 0 ? (v / total) * 100 : 0;
              return `${ctx.label}: ${formatPct(pct)}`;
            },
          },
        },
      },
    };

    chartRef.current = new ChartJS<"doughnut">(canvas, {
      type: "doughnut",
      data: {
        labels: data.map((d) => d.label),
        datasets: [
          {
            data: data.map((d) => d.value),
            backgroundColor: data.map((d) => d.color),
            borderColor: "#FAF8F4",
            borderWidth: 2,
          },
        ],
      },
      options,
    });

    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [data, total]);

  return (
    <div className="relative h-full w-full" role="img" aria-label={ariaLabel}>
      <canvas ref={canvasRef} />
      {(centerLabel !== undefined || centerValue !== undefined) && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          {centerLabel !== undefined && (
            <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
              {centerLabel}
            </span>
          )}
          {centerValue !== undefined && (
            <span className="font-serif text-lg font-medium text-ink">{centerValue}</span>
          )}
        </div>
      )}
    </div>
  );
}
