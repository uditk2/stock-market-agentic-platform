"use client";

/**
 * Poll an async source on an interval.
 *
 * Stale results from a superseded request are discarded, so a slow response
 * cannot overwrite newer data that arrived while it was in flight.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export function usePoll<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  deps: unknown[] = [],
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const generation = useRef(0);

  const run = useCallback(async () => {
    const mine = ++generation.current;
    try {
      const result = await fetcher();
      if (mine === generation.current) {
        setData(result);
        setError(null);
      }
    } catch (cause) {
      if (mine === generation.current) {
        setError(cause instanceof Error ? cause.message : String(cause));
      }
    } finally {
      if (mine === generation.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
    if (intervalMs <= 0) return;
    const timer = setInterval(run, intervalMs);
    return () => clearInterval(timer);
  }, [run, intervalMs]);

  return { data, error, loading, refresh: run };
}
