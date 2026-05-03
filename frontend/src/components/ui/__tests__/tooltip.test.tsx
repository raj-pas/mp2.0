/**
 * Tier 3 polish coverage — Radix tooltip wrapper (§1.10).
 *
 * Smoke-level: verifies the wrapper composes into a valid React tree
 * + the public surface (TooltipProvider, Tooltip, TooltipTrigger,
 * TooltipContent) is reachable. Radix's tooltip is portal-rendered
 * + only mounts content on hover/focus, so a full open-on-hover
 * test would need pointer-event simulation that's out-of-scope for
 * Vitest's jsdom environment. The behavior is covered indirectly
 * by the cross-browser Playwright smoke spec.
 */
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../tooltip";

describe("Tooltip wrapper", () => {
  it("renders the trigger by default (content gated by hover/focus)", () => {
    const { getByText } = render(
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button">trigger</button>
          </TooltipTrigger>
          <TooltipContent>content</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    expect(getByText("trigger")).toBeInTheDocument();
  });

  it("composes without runtime errors when nested", () => {
    expect(() =>
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <span>nested-trigger</span>
            </TooltipTrigger>
            <TooltipContent>nested-content</TooltipContent>
          </Tooltip>
        </TooltipProvider>,
      ),
    ).not.toThrow();
  });

  it("accepts custom delayDuration prop on Provider", () => {
    expect(() =>
      render(
        <TooltipProvider delayDuration={500}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button">x</button>
            </TooltipTrigger>
            <TooltipContent>delayed</TooltipContent>
          </Tooltip>
        </TooltipProvider>,
      ),
    ).not.toThrow();
  });
});
