import { useCallback, useEffect, useState } from "react";

/**
 * Strictly-typed localStorage hook for UI prefs (locked decision #32b).
 *
 * NEVER store PII. Allowed payloads: enum-like strings, external_ids
 * (UUIDs), simple booleans/numbers.
 */
export function useLocalStorage<T>(key: string, initial: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => readKey(key, initial));

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Ignore quota / privacy-mode failures; UI prefs are best-effort.
    }
  }, [key, value]);

  const setStored = useCallback((next: T) => setValue(next), []);
  return [value, setStored];
}

function readKey<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}
