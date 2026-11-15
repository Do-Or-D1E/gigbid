import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { onApiProblem } from "./client";
import { endpoints } from "./endpoints";
import type { components } from "./api/schema";

type Health = components["schemas"]["HealthOut"];

interface HealthState {
  health: Health | null;
  marketplaceDown: boolean;
  detail: string;
  /** Called when an API call returned 503 or a stream sent marketplace_down. */
  reportDown: (detail?: string) => void;
}

const Ctx = createContext<HealthState | null>(null);
export const HEALTH_POLL_MS = 15000;

export function HealthProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [forcedDetail, setForcedDetail] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const h = await endpoints.health();
      setHealth(h);
      // A healthy poll clears a 503-triggered banner.
      if (h.marketplace === "up") setForcedDetail(null);
    } catch {
      /* health is advisory; keep last known state */
    }
  }, []);

  useEffect(() => {
    void poll();
    const t = setInterval(() => void poll(), HEALTH_POLL_MS);
    return () => clearInterval(t);
  }, [poll]);

  const reportDown = useCallback((d?: string) => setForcedDetail(d || "The marketplace did not respond."), []);

  useEffect(
    () =>
      onApiProblem((status, detail) => {
        if (status === 503) setForcedDetail(detail);
      }),
    [],
  );

  const value = useMemo<HealthState>(() => {
    const down = health?.marketplace === "down" || forcedDetail !== null;
    return {
      health,
      marketplaceDown: down,
      detail: (health?.marketplace === "down" ? health.marketplace_detail : "") || forcedDetail || "",
      reportDown,
    };
  }, [health, forcedDetail, reportDown]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useHealth(): HealthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useHealth outside HealthProvider");
  return v;
}
