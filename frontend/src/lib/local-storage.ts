import { useCallback, useSyncExternalStore } from "react";

/**
 * Strictly-typed localStorage hook for UI prefs (locked decision #32b).
 *
 * NEVER store PII. Allowed payloads: enum-like strings, external_ids
 * (UUIDs), simple booleans/numbers.
 *
 * Implementation note: every consumer of the same key shares state via
 * a per-key subscriber set. Without this, two components reading the
 * same key would each hold their own `useState` copy — writes from one
 * would update localStorage but the other component's React state
 * would stay stale until it re-mounted. We learned this the hard way
 * during the R3 smoke run: `useRememberedClientId()` was called from
 * both TopBar (writer) and the routes (readers), and the routes never
 * saw the updated id. `useSyncExternalStore` makes the two views
 * coherent and also picks up cross-tab `storage` events.
 */
type Listener = () => void;
const listeners = new Map<string, Set<Listener>>();
const cache = new Map<string, string | null>();

function getRaw(key: string): string | null {
  if (cache.has(key)) return cache.get(key) ?? null;
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    cache.set(key, raw);
    return raw;
  } catch {
    return null;
  }
}

function setRaw(key: string, raw: string | null): void {
  if (typeof window !== "undefined") {
    try {
      if (raw === null) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, raw);
      }
    } catch {
      // Ignore quota / privacy-mode failures; UI prefs are best-effort.
    }
  }
  cache.set(key, raw);
  const set = listeners.get(key);
  if (set !== undefined) {
    for (const fn of set) fn();
  }
}

function subscribe(key: string, listener: Listener): () => void {
  let set = listeners.get(key);
  if (set === undefined) {
    set = new Set();
    listeners.set(key, set);
  }
  set.add(listener);

  // Cross-tab sync: listen for storage events on the window.
  const onStorage = (event: StorageEvent) => {
    if (event.key === key) {
      cache.set(key, event.newValue);
      listener();
    }
  };
  if (typeof window !== "undefined") {
    window.addEventListener("storage", onStorage);
  }

  return () => {
    set.delete(listener);
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", onStorage);
    }
  };
}

export function useLocalStorage<T>(key: string, initial: T): [T, (value: T) => void] {
  const getSnapshot = useCallback(() => getRaw(key), [key]);
  const subscribeKey = useCallback((listener: Listener) => subscribe(key, listener), [key]);

  const raw = useSyncExternalStore(subscribeKey, getSnapshot, getSnapshot);

  const value: T = parseOrInitial(raw, initial);

  const setValue = useCallback(
    (next: T) => {
      try {
        setRaw(key, JSON.stringify(next));
      } catch {
        // Ignore JSON serialization failures (e.g. circular refs).
      }
    },
    [key],
  );

  return [value, setValue];
}

function parseOrInitial<T>(raw: string | null, initial: T): T {
  if (raw === null) return initial;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return initial;
  }
}
