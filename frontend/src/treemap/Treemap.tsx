import { hierarchy, treemap as d3treemap, treemapSquarify } from "d3-hierarchy";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatCadCompact } from "../lib/format";
import { colorForNode, type TreemapMode, type TreemapNode } from "../lib/treemap";
import { cn } from "../lib/cn";

interface TreemapProps {
  root: TreemapNode;
  mode: TreemapMode;
  onSelect?: (node: TreemapNode) => void;
  /**
   * P7 (plan v20 §A1.35 / G9): which allocation dataset the parent is
   * passing in. `'current'` is sourced from `household.committed_allocation`
   * via `useTreemap`; `'ideal'` is derived from
   * `latest_portfolio_run.output.account_rollups`. Drives the
   * empty-state copy + aria-label suffix; the component does not fetch
   * either source directly (parent owns data assembly).
   */
  dataset?: "current" | "ideal";
}

/**
 * Squarified treemap rendered as SVG rects.
 *
 * Per locked decision #2, this component renders pre-computed
 * hierarchical data from `/api/treemap/`. d3-hierarchy handles the
 * layout math; this component focuses on accessible/aesthetic SVG.
 *
 * Click + Enter/Space drill into the corresponding node — for
 * by-account/by-goal modes, the parent route observes selection
 * to navigate (e.g., HouseholdRoute → click account leaf → push
 * `/account/:id`).
 */
export function Treemap({ root, mode, onSelect, dataset = "current" }: TreemapProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 480 });

  useEffect(() => {
    const element = containerRef.current;
    if (element === null) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setSize({ width, height });
        }
      }
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const layout = useMemo(() => {
    const layoutRoot = hierarchy<TreemapNode>(root, (d) => d.children)
      .sum((d) => (d.children && d.children.length > 0 ? 0 : (d.value ?? 0)))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    return d3treemap<TreemapNode>()
      .tile(treemapSquarify)
      .size([size.width, size.height])
      .padding(2)
      .round(true)(layoutRoot);
  }, [root, size]);

  const leaves = layout.leaves();
  const totalValue = root.children
    ? root.children.reduce((s, c) => s + (c.value ?? 0), 0)
    : (root.value ?? 0);

  if (totalValue <= 0 || leaves.length === 0) {
    return (
      <div
        ref={containerRef}
        className="flex h-full w-full items-center justify-center bg-paper-2"
        data-testid={dataset === "ideal" ? "treemap-ideal-empty" : undefined}
      >
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {dataset === "ideal" ? t("treemap.no_recommendation_yet") : t("treemap.empty")}
        </p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative h-full w-full bg-paper-2">
      <svg
        width={size.width}
        height={size.height}
        viewBox={`0 0 ${size.width} ${size.height}`}
        role="img"
        aria-label={t("treemap.aria_label", { mode: t(`treemap.mode_${mode}`) })}
        data-dataset={dataset}
      >
        {/*
          Plan v20 §A1.36 (P12): SVG pattern for the virtual `_unallocated`
          tile. Diagonal stripes signal "unfunded / not assigned" — same
          visual idiom as YNAB's "Ready to Assign" hot-pink CTA + Quicken's
          "uncategorized" highlight. Border is dashed in the rect itself.
        */}
        <defs>
          <pattern
            id="treemap-unallocated-pattern"
            width="8"
            height="8"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" fill="#F1EDE5" />
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="8"
              stroke="#B87333"
              strokeWidth="2"
              opacity="0.55"
            />
          </pattern>
        </defs>
        {leaves.map((leaf, idx) => {
          const node = leaf.data;
          const x0 = leaf.x0 ?? 0;
          const y0 = leaf.y0 ?? 0;
          const x1 = leaf.x1 ?? 0;
          const y1 = leaf.y1 ?? 0;
          const w = x1 - x0;
          const h = y1 - y0;
          const value = leaf.value ?? 0;
          const parentLabel = leaf.parent?.data.label;
          const isUnallocated = node.unallocated === true;
          const fill = isUnallocated
            ? "url(#treemap-unallocated-pattern)"
            : colorForNode(node, mode, idx);
          const interactive = onSelect !== undefined;
          return (
            <g
              key={node.id}
              transform={`translate(${x0}, ${y0})`}
              tabIndex={interactive ? 0 : -1}
              role={interactive ? "button" : "img"}
              aria-label={
                isUnallocated
                  ? `${t("treemap_extras.unallocated_label")} ${node.label}, ${formatCadCompact(value)}`
                  : `${node.label}, ${formatCadCompact(value)}`
              }
              data-testid={isUnallocated ? "treemap-unallocated-tile" : undefined}
              onClick={() => onSelect?.(node)}
              onKeyDown={(event) => {
                if (!interactive) return;
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect?.(node);
                }
              }}
              className={cn("group focus:outline-none", interactive && "cursor-pointer")}
            >
              <rect
                width={w}
                height={h}
                fill={fill}
                stroke={isUnallocated ? "#B87333" : "rgba(14,17,22,0.18)"}
                strokeWidth={isUnallocated ? 2 : 1}
                strokeDasharray={isUnallocated ? "6 4" : undefined}
                className="transition-[filter] duration-150 group-hover:[filter:brightness(1.08)] group-focus-visible:[filter:brightness(1.12)] group-focus-visible:[stroke-width:2]"
              />
              {w > 64 && h > 28 && (
                <>
                  {parentLabel !== undefined && parentLabel !== node.label && (
                    <text
                      x={8}
                      y={16}
                      fontFamily="JetBrains Mono"
                      fontSize={9}
                      letterSpacing="0.12em"
                      fill={isUnallocated ? "#1A1F26" : "rgba(255,255,255,0.78)"}
                      style={{ textTransform: "uppercase" }}
                    >
                      {truncate(parentLabel, w / 6)}
                    </text>
                  )}
                  <text
                    x={8}
                    y={parentLabel !== undefined && parentLabel !== node.label ? 32 : 22}
                    fontFamily="Inter Tight"
                    fontWeight={600}
                    fontSize={13}
                    fill={isUnallocated ? "#0E1116" : "#FAF8F4"}
                  >
                    {truncate(node.label, w / 7)}
                  </text>
                </>
              )}
              {w > 90 && h > 50 && (
                <text
                  x={8}
                  y={h - 10}
                  fontFamily="Fraunces"
                  fontSize={14}
                  fill={isUnallocated ? "#1A1F26" : "rgba(255,255,255,0.95)"}
                >
                  {formatCadCompact(value)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function truncate(value: string, maxChars: number): string {
  const limit = Math.max(3, Math.floor(maxChars));
  if (value.length <= limit) return value;
  return `${value.slice(0, limit - 1)}…`;
}
