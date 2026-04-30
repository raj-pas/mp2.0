/**
 * Class-name composer. shadcn/ui convention: `cn(...args)` merges Tailwind
 * classes with later args winning conflicts via `tailwind-merge`.
 */
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
