/**
 * Lognormal projection fan chart (v35 restyled per locked decision #21).
 *
 * Driven by `/api/preview/projection-paths/` for the band data and
 * `/api/preview/probability/` for the "X% chance of reaching target"
 * callout. Per locked decision #2 the engine math is server-side; this
 * component does layout + styling only.
 *
 * Visual contract per the plan:
 *   - Cream paper-2 background; hairline borders
 *   - Outer band fill (P10–P90) + inner band fill (P25–P75)
 *   - Dotted median (P50) line
 *   - Amber dashed target horizontal line when a target value is passed
 *   - Year/value tooltip on hover
 *
 * R4 ships the static rendering + target-line probability badge; the
 * hover-debounced probability fetch the plan describes is queued for
 * a follow-up commit (locked decision #18 latency budget; the static
 * badge already conveys the headline number).
 */
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  type ChartOptions,
  type ChartDataset,
} from "chart.js";
import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";

import { formatCadCompact, formatPct } from "../lib/format";
import { type ProjectionPath } from "../lib/preview";

ChartJS.register(
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Filler,
  Tooltip,
  Legend,
  Title,
);

interface FanChartProps {
  paths: ProjectionPath[];
  targetValue?: number | null;
  /** Pre-computed P[ value at horizon ≥ target ], 0..1. */
  probabilityAtTarget?: number | null;
  ariaLabel?: string;
  /** Tier label appended to the legend chip (e.g. "need", "want"). */
  tierLabel?: string;
}

/**
 * Render a Chart.js line fan with multi-band fills.
 *
 * The bands are specified by which two percentile paths (sorted)
 * delimit the area. We pull P10/P25/P50/P75/P90 from `paths` and
 * fall back gracefully if the upstream returned a different
 * percentile set (R4 calls with [0.1, 0.25, 0.5, 0.75, 0.9]).
 */
export function FanChart({
  paths,
  targetValue,
  probabilityAtTarget,
  ariaLabel,
  tierLabel,
}: FanChartProps) {
  const { t } = useTranslation();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<ChartJS<"line"> | null>(null);

  const layout = useMemo(() => buildLayout(paths), [paths]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) return;
    if (layout === null) return;

    ChartJS.getChart(canvas)?.destroy();

    const datasets: ChartDataset<"line">[] = [];
    if (layout.p10 !== null && layout.p90 !== null) {
      datasets.push({
        label: "P10",
        data: layout.p10,
        borderColor: "rgba(46, 93, 58, 0)",
        backgroundColor: "rgba(46, 93, 58, 0.10)",
        fill: false,
        pointRadius: 0,
        tension: 0.2,
      });
      datasets.push({
        label: "P90",
        data: layout.p90,
        borderColor: "rgba(46, 93, 58, 0)",
        backgroundColor: "rgba(46, 93, 58, 0.10)",
        fill: "-1",
        pointRadius: 0,
        tension: 0.2,
      });
    }
    if (layout.p25 !== null && layout.p75 !== null) {
      datasets.push({
        label: "P25",
        data: layout.p25,
        borderColor: "rgba(46, 93, 58, 0)",
        backgroundColor: "rgba(46, 93, 58, 0.20)",
        fill: false,
        pointRadius: 0,
        tension: 0.2,
      });
      datasets.push({
        label: "P75",
        data: layout.p75,
        borderColor: "rgba(46, 93, 58, 0)",
        backgroundColor: "rgba(46, 93, 58, 0.20)",
        fill: "-1",
        pointRadius: 0,
        tension: 0.2,
      });
    }
    if (layout.p50 !== null) {
      datasets.push({
        label: t("fan_chart.median"),
        data: layout.p50,
        borderColor: "rgba(14,17,22,0.78)",
        backgroundColor: "rgba(14,17,22,0)",
        borderDash: [4, 4],
        fill: false,
        pointRadius: 0,
        tension: 0,
      });
    }
    if (typeof targetValue === "number" && targetValue > 0) {
      // Horizontal target line as a constant series.
      datasets.push({
        label: "Target",
        data: layout.labels.map(() => targetValue),
        borderColor: "rgba(197, 165, 114, 0.95)",
        backgroundColor: "rgba(197, 165, 114, 0)",
        borderDash: [6, 4],
        borderWidth: 2,
        fill: false,
        pointRadius: 0,
        tension: 0,
      });
    }

    const options: ChartOptions<"line"> = {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => {
              const first = items[0];
              return first === undefined
                ? ""
                : t("fan_chart.hover_year_pill", { year: first.label });
            },
            label: (ctx) => {
              const v = Number(ctx.parsed.y) || 0;
              return `${ctx.dataset.label ?? ""}: ${formatCadCompact(v)}`;
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: t("fan_chart.axis_year") },
          grid: { color: "rgba(14,17,22,0.06)" },
        },
        y: {
          title: { display: true, text: t("fan_chart.axis_value") },
          ticks: {
            callback: (value) => formatCadCompact(Number(value)),
          },
          grid: { color: "rgba(14,17,22,0.06)" },
        },
      },
    };

    chartRef.current = new ChartJS<"line">(canvas, {
      type: "line",
      data: { labels: layout.labels.map((y) => y.toFixed(0)), datasets },
      options,
    });

    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [layout, targetValue, t]);

  if (layout === null) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-paper-2">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("fan_chart.no_data")}
        </p>
      </div>
    );
  }

  return (
    <div
      className="relative h-full w-full"
      role="img"
      aria-label={ariaLabel ?? t("fan_chart.aria_label")}
    >
      <canvas ref={canvasRef} />
      {tierLabel !== undefined && (
        <span className="absolute right-2 top-2 inline-flex items-center gap-1 border border-hairline bg-paper px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest text-muted">
          {t("fan_chart.tier_band", { tier: tierLabel })}
        </span>
      )}
      {typeof probabilityAtTarget === "number" &&
        targetValue !== null &&
        targetValue !== undefined && (
          <span className="absolute left-2 bottom-2 inline-flex items-center gap-2 border border-accent bg-paper px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-ink">
            <span aria-hidden className="h-2 w-2" style={{ background: "#C5A572" }} />
            {t("fan_chart.probability_callout", {
              pct: formatPct(probabilityAtTarget * 100, 0),
              year: layout.labels[layout.labels.length - 1]?.toFixed(0) ?? "—",
            })}
          </span>
        )}
    </div>
  );
}

type ChartLayout = {
  labels: number[];
  p10: number[] | null;
  p25: number[] | null;
  p50: number[] | null;
  p75: number[] | null;
  p90: number[] | null;
};

function buildLayout(paths: ProjectionPath[]): ChartLayout | null {
  if (paths.length === 0) return null;
  const byPercentile = new Map<number, ProjectionPath>();
  for (const path of paths) byPercentile.set(round2(path.percentile), path);

  const reference = paths[0];
  if (reference === undefined || reference.points.length === 0) return null;
  const labels = reference.points.map((pt) => pt.year);

  const series = (p: number) => {
    const path = byPercentile.get(round2(p));
    if (path === undefined) return null;
    return labels.map((year) => {
      const point = path.points.find((pt) => Math.abs(pt.year - year) < 1e-6);
      return point !== undefined ? point.value : 0;
    });
  };

  const p10 = series(0.1);
  const p25 = series(0.25);
  const p50 = series(0.5);
  const p75 = series(0.75);
  const p90 = series(0.9);

  if (p10 === null && p25 === null && p50 === null && p75 === null && p90 === null) {
    return null;
  }

  return { labels, p10, p25, p50, p75, p90 };
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
