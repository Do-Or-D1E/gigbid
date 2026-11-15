import { useCallback, useEffect, useRef, useState } from "react";
import { runStreamUrl } from "./client";
import { isStreamEnd, type StreamEvent } from "./timeline";

export type StreamState = "idle" | "connecting" | "live" | "ended" | "dropped";

const EVENT_NAMES = ["start", "end", "update", "interrupt", "marketplace_down", "error", "queued", "done", "ping", "message", "custom"];

/**
 * Subscribe to GET /api/runs/{id}/stream (SSE). In serverless mode opening the stream is what executes the run.
 * Reconnects with ?after=<last id> if the connection drops before the final `end` event.
 */
export function useRunStream(runId: string | null | undefined, opts: { onEnd?: () => void } = {}) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [state, setState] = useState<StreamState>("idle");
  const [attempt, setAttempt] = useState(0);
  const onEnd = useRef(opts.onEnd);
  onEnd.current = opts.onEnd;
  const lastId = useRef(0);

  useEffect(() => {
    setEvents([]);
    lastId.current = 0;
    if (!runId) {
      setState("idle");
      return;
    }
    setState("connecting");
    let closed = false;
    let failures = 0;
    let es: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const finish = () => {
      closed = true;
      es?.close();
      setState("ended");
      onEnd.current?.();
    };

    const handle = (raw: MessageEvent, name: string) => {
      if (name === "ping" || !raw.data) return;
      let data: Partial<StreamEvent> = {};
      try {
        data = JSON.parse(raw.data);
      } catch {
        return;
      }
      const id = typeof data.id === "number" ? data.id : Number(raw.lastEventId) || lastId.current + 1;
      const ev: StreamEvent = { id, ts: data.ts ?? new Date().toISOString(), kind: data.kind || name, node: data.node, payload: data.payload };
      if (id <= lastId.current && lastId.current !== 0 && !isStreamEnd(ev)) return; // duplicate after a resume
      lastId.current = Math.max(lastId.current, id);
      failures = 0;
      setState("live");
      setEvents((prev) => (prev.some((p) => p.id === ev.id && p.kind === ev.kind) ? prev : [...prev, ev]));
      if (isStreamEnd(ev)) finish();
    };

    const connect = () => {
      if (closed) return;
      es = new EventSource(runStreamUrl(runId, lastId.current || undefined));
      for (const name of EVENT_NAMES) es.addEventListener(name, (e) => handle(e as MessageEvent, name));
      es.onmessage = (e) => handle(e, "message");
      es.onopen = () => setState((s) => (s === "connecting" ? "live" : s));
      es.onerror = () => {
        if (closed) return;
        es?.close();
        failures += 1;
        if (failures > 4) {
          closed = true;
          setState("dropped");
          return;
        }
        // resume from the last seen event
        retryTimer = setTimeout(connect, Math.min(1000 * failures, 4000));
      };
    };
    connect();

    return () => {
      closed = true;
      es?.close();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [runId, attempt]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);
  return { events, state, retry };
}
