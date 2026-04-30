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
export function Treemap({ root, mode, onSelect }: TreemapProps) {
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
      <div ref={containerRef} className="flex h-full w-full items-center justify-center bg-paper-2">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("treemap.empty")}
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
      >
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
          const fill = colorForNode(node, mode, idx);
          const interactive = onSelect !== undefined;
          return (
            <g
              key={node.id}
              transform={`translate(${x0}, ${y0})`}
              tabIndex={interactive ? 0 : -1}
              role={interactive ? "button" : "img"}
              aria-label={`${node.label}, ${formatCadCompact(value)}`}
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
                stroke="rgba(14,17,22,0.18)"
                strokeWidth={1}
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
                      fill="rgba(255,255,255,0.78)"
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
                    fill="#FAF8F4"
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
                  fill="rgba(255,255,255,0.95)"
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
