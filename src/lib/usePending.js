import { useCallback, useEffect, useState } from "react";

/**
 * Tracks whether any request a page has started is still in flight.
 *
 *   const [pending, track] = usePending();
 *   track(yieldApi.trend(season)).then(...)
 *
 * `track` returns the same promise, so it drops into an existing chain. `pending`
 * stays true until every tracked request has settled — including one whose result
 * the page no longer wants (a filter changed twice): the user is still waiting on
 * the newer one.
 */
export function usePending() {
  const [count, setCount] = useState(0);
  const track = useCallback((promise) => {
    setCount((c) => c + 1);
    const done = () => setCount((c) => Math.max(0, c - 1));
    promise.then(done, done);
    return promise;
  }, []);
  return [count > 0, track];
}

/**
 * `flag`, but it only turns on after it has been true for `delay` ms, and it turns
 * off at once. Keeps a loading indicator from flashing on responses that come
 * back instantly (cached data).
 */
export function useDelayedFlag(flag, delay = 150) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!flag) {
      setShown(false);
      return undefined;
    }
    const t = setTimeout(() => setShown(true), delay);
    return () => clearTimeout(t);
  }, [flag, delay]);
  return shown;
}
