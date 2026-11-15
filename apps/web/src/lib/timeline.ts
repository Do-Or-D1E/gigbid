import type { AnyRec } from "./types";

export interface StreamEvent {
  id: number;
  ts: string;
  kind: string;
  node?: string | null;
  payload?: AnyRec;
}

export type NodeStatus = "running" | "done" | "error" | "waiting";
export interface NodeRow {
  key: string;
  node: string;
  status: NodeStatus;
  startedAt?: string;
  latency_s?: number;
  tokens?: number;
  summary?: string;
}
export interface Timeline {
  nodes: NodeRow[];
  notes: { id: number; tone: "info" | "warn" | "error"; text: string }[];
  queued: boolean;
  interrupted: boolean;
  marketplaceDown: boolean;
  marketplaceDetail?: string;
  error?: string;
  ended: boolean;
}

export function tokenTotal(t: unknown): number | undefined {
  if (typeof t === "number") return t;
  if (t && typeof t === "object") {
    const o = t as AnyRec;
    if (typeof o.total === "number") return o.total;
    const s = (Number(o.input) || 0) + (Number(o.output) || 0) + (Number(o.input_tokens) || 0) + (Number(o.output_tokens) || 0);
    return s || undefined;
  }
  return undefined;
}

/** The stream ends with an `end` event that carries no node; node-level start/end events do carry one. */
export function isStreamEnd(ev: StreamEvent): boolean {
  const node = ev.node || ev.payload?.node;
  if (ev.kind === "done") return true;
  return ev.kind === "end" && !node;
}

function str(v: unknown): string | undefined {
  if (typeof v === "string") return v;
  if (v == null) return undefined;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

export function buildTimeline(events: StreamEvent[]): Timeline {
  const nodes: NodeRow[] = [];
  const notes: Timeline["notes"] = [];
  const tl: Timeline = { nodes, notes, queued: false, interrupted: false, marketplaceDown: false, ended: false };
  const open = new Map<string, NodeRow>();

  const upsert = (name: string, ev: StreamEvent, fresh: boolean): NodeRow => {
    let row = open.get(name);
    if (!row || fresh) {
      row = { key: `${name}-${nodes.length}`, node: name, status: "running", startedAt: ev.ts };
      nodes.push(row);
      open.set(name, row);
    }
    return row;
  };

  for (const ev of events) {
    const p = ev.payload ?? {};
    const node: string | undefined = (ev.node as string | undefined) || (p.node as string | undefined) || undefined;
    switch (ev.kind) {
      case "queued":
        tl.queued = true;
        break;
      case "start":
      case "end": {
        if (!node) {
          if (ev.kind === "end") tl.ended = true;
          break;
        }
        const evName = typeof p.event === "string" ? p.event : ev.kind;
        const isEnd = /end|finish|complete|done/i.test(evName) && !/start/i.test(evName);
        if (!isEnd) {
          upsert(node, ev, true);
        } else {
          const row = upsert(node, ev, !open.has(node));
          row.status = "done";
          if (typeof p.latency_s === "number") row.latency_s = p.latency_s;
          const tk = tokenTotal(p.tokens);
          if (tk !== undefined) row.tokens = tk;
          if (p.summary) row.summary = str(p.summary);
          open.delete(node);
        }
        break;
      }
      case "update": {
        const name = node || Object.keys(p).find((k) => !["summary", "latency_s", "tokens"].includes(k));
        if (!name) break;
        const row = upsert(name, ev, !open.has(name));
        row.status = "done";
        if (typeof p.latency_s === "number") row.latency_s = p.latency_s;
        const tk = tokenTotal(p.tokens);
        if (tk !== undefined) row.tokens = tk;
        if (p.summary) row.summary = str(p.summary);
        open.delete(name);
        break;
      }
      case "interrupt": {
        tl.interrupted = true;
        const row: NodeRow = { key: `interrupt-${ev.id}`, node: node || "approval", status: "waiting", startedAt: ev.ts, summary: "Waiting for your decision." };
        nodes.push(row);
        break;
      }
      case "marketplace_down":
        tl.marketplaceDown = true;
        tl.marketplaceDetail = str(p.detail ?? p.message);
        notes.push({ id: ev.id, tone: "warn", text: "Marketplace unavailable. Work is queued and will resume automatically." });
        break;
      case "error": {
        const msg = str(p.message ?? p.error ?? p.detail) || "The run reported an error.";
        tl.error = msg;
        if (node && open.has(node)) {
          open.get(node)!.status = "error";
          open.get(node)!.summary = msg;
        }
        notes.push({ id: ev.id, tone: "error", text: msg });
        break;
      }
      default:
        break;
    }
  }
  // A finished stream has no node still "running".
  if (tl.ended) for (const r of nodes) if (r.status === "running") r.status = "done";
  return tl;
}
