import { useMemo } from "react";
import { buildTimeline, type StreamEvent, type NodeStatus } from "../lib/timeline";
import { num, seconds } from "../lib/format";

const STATUS_TEXT: Record<NodeStatus, string> = {
  running: "Running",
  done: "Done",
  error: "Failed",
  waiting: "Waiting",
};

/** Ordered list of agent nodes with status, latency, tokens and a one-line summary. */
export default function RunTimeline({ events, live = false }: { events: StreamEvent[]; live?: boolean }) {
  const tl = useMemo(() => buildTimeline(events), [events]);
  if (tl.nodes.length === 0) {
    return (
      <p className="muted" role="status">
        {live ? (tl.queued ? "Run queued. Waiting for the first step..." : "Connecting to the run...") : "No step events were recorded for this run."}
      </p>
    );
  }
  return (
    <ol className="timeline" aria-label="Run steps" data-testid="run-timeline">
      {tl.nodes.map((n) => (
        <li key={n.key} className={`timeline__item timeline__item--${n.status}`}>
          <span className="timeline__dot" aria-hidden="true" />
          <div className="timeline__body">
            <div className="timeline__head">
              <strong className="timeline__node">{n.node.replace(/_/g, " ")}</strong>
              <span className={`pill pill--${n.status}`}>{STATUS_TEXT[n.status]}</span>
              {n.latency_s !== undefined && <span className="muted small">{seconds(n.latency_s)}</span>}
              {n.tokens !== undefined && <span className="muted small">{num(n.tokens)} tokens</span>}
            </div>
            {n.summary && <p className="timeline__summary">{n.summary}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
