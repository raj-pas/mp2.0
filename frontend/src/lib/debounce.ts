import { useEffect, useState } from "react";

/**
 * Returns `value` debounced by `delayMs` (default 300ms per locked
 * decision #18). Pair with TanStack Query: pass the debounced value as
 * part of the query key so the network call only fires once the user
 * stops typing/dragging.
 */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);

  return debounced;
}
