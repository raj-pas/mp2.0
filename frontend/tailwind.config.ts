import type { Config } from "tailwindcss";

/**
 * v36 design tokens — paper/ink/copper/gold aesthetic per locked decision #5
 * (canon-aligned vocabulary) + #12 (a11y baseline) + #22d (self-hosted fonts).
 *
 * Bucket colors (`buckets.*`) match the canon 5-band risk descriptors:
 * Cautious / Conservative-balanced / Balanced / Balanced-growth / Growth-oriented.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // v36 mockup palette
        ink: {
          DEFAULT: "#0E1116",
          2: "#1A1F26",
        },
        paper: {
          DEFAULT: "#FAF8F4",
          2: "#F1EDE5",
        },
        accent: {
          DEFAULT: "#C5A572", // gold
          2: "#8B5E3C", // copper
        },
        hairline: {
          DEFAULT: "rgba(14,17,22,0.10)",
          2: "rgba(14,17,22,0.18)",
        },
        muted: {
          DEFAULT: "#6B7280",
          2: "#9CA3AF",
        },
        // Risk band colors (canon-aligned descriptors)
        buckets: {
          cautious: "#5D7A8C", // Cautious (low)
          "conservative-balanced": "#6B8E8E", // Conservative-balanced
          balanced: "#C5A572", // Balanced
          "balanced-growth": "#B87333", // Balanced-growth
          "growth-oriented": "#8B2E2E", // Growth-oriented
        },
        // Semantic
        success: "#2E5D3A",
        danger: "#8B2E2E",
        info: "#2E4A6B",
        // v36 fund palette (matches engine/sleeves.py SLEEVE_COLOR_HEX)
        funds: {
          "sh-sav": "#5D7A8C", // slate
          "sh-inc": "#2E4A6B", // navy
          "sh-eq": "#0E1116", // ink
          "sh-glb": "#8B5E3C", // copper
          "sh-sc": "#B87333", // orange
          "sh-gsc": "#2E5D3A", // green
          "sh-fnd": "#6B5876", // plum
          "sh-bld": "#8B8C5E", // olive
        },
        // Legacy tokens (kept for transitional code; remove in R7)
        mist: "#eef3f1",
        spruce: "#1f5d50",
        copper: "#b5673f",
        citrine: "#d7a928",
        skyglass: "#dcebf2",
      },
      fontFamily: {
        // Self-hosted fonts (locked decision #22d).
        // .woff2 files served from /fonts/* via @font-face declarations
        // in src/index.css; configured in R0 follow-up step.
        serif: ["Fraunces", "Georgia", "serif"],
        sans: ["Inter Tight", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        // Mockup uses 0.06–0.18em on JetBrains Mono uppercase labels.
        wider: "0.06em",
        widest: "0.14em",
        ultrawide: "0.18em",
      },
      borderRadius: {
        // Mockup uses square corners — no rounded by default.
        none: "0",
      },
      boxShadow: {
        sm: "0 1px 2px rgba(14,17,22,0.04)",
        DEFAULT: "0 4px 12px rgba(14,17,22,0.06)",
        lg: "0 16px 48px rgba(14,17,22,0.08)",
        soft: "0 12px 36px rgba(23, 33, 31, 0.08)", // legacy alias
      },
    },
  },
  plugins: [],
} satisfies Config;
