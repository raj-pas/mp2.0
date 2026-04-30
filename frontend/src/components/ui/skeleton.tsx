import * as React from "react";

import { cn } from "../../lib/cn";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="status"
      aria-busy="true"
      className={cn("animate-pulse bg-paper-2", className)}
      {...props}
    />
  );
}

export { Skeleton };
