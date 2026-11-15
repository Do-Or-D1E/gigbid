import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "./client";

export interface AsyncState<T> {
  data: T | undefined;
  error: string | null;
  status: number | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: (d: T) => void;
}

/** Load data on mount and when deps change. Polling reloads are silent (no skeleton flash). */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], opts: { intervalMs?: number } = {}): AsyncState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const seq = useRef(0);

  const run = useCallback(async (silent: boolean) => {
    const my = ++seq.current;
    if (!silent) setLoading(true);
    try {
      const d = await fnRef.current();
      if (my !== seq.current) return;
      setData(d);
      setError(null);
      setStatus(null);
    } catch (e) {
      if (my !== seq.current) return;
      setError(errorMessage(e));
      setStatus((e as { status?: number }).status ?? 0);
    } finally {
      if (my === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void run(false);
    return () => {
      seq.current++;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (!opts.intervalMs) return;
    const t = setInterval(() => void run(true), opts.intervalMs);
    return () => clearInterval(t);
  }, [opts.intervalMs, run]);

  return { data, error, status, loading, reload: () => run(true), setData };
}

/** Wrap an async action with busy and error state. */
export function useAction<A extends unknown[], R>(fn: (...a: A) => Promise<R>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const call = useCallback(async (...a: A): Promise<R | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await fnRef.current(...a);
    } catch (e) {
      setError(errorMessage(e));
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);
  return { call, busy, error, clearError: () => setError(null) };
}

export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} - GigBid`;
  }, [title]);
}
