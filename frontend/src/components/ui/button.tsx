import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "../../lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-sans text-[11px] font-medium tracking-wide transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 focus-visible:ring-offset-paper disabled:pointer-events-none disabled:opacity-35",
  {
    variants: {
      variant: {
        default: "bg-ink text-paper hover:bg-accent-2",
        outline: "border border-hairline-2 bg-paper text-ink hover:bg-paper-2",
        ghost: "bg-transparent text-muted hover:text-ink",
        toggle:
          "bg-paper-2 text-muted hover:text-ink data-[on=true]:bg-ink data-[on=true]:text-paper",
        link: "text-ink underline-offset-2 hover:underline",
        destructive: "bg-danger text-paper hover:opacity-90",
      },
      size: {
        default: "h-7 px-3",
        sm: "h-6 px-2 text-[10px]",
        lg: "h-8 px-4 text-[12px]",
        icon: "h-7 w-7",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
