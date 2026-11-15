import { useEffect, useMemo, type ReactNode } from "react";
import { Link } from "react-router-dom";
import RunTimeline from "./RunTimeline";
import { useRunStream } from "../lib/stream";
import { buildTimeline } from "../lib/timeline";
import { useHealth } from "../lib/health";

interface Props {
  runId: string;
  title?: string;
  onEnd?: () => void;
  onClose?: () => void;
  /** Shown once the run is waiting for the user's decision. */
  whenInterrupted?: ReactNode;
}

/** Opens the run's SSE stream and shows the live timeline. Used after every action that returns a RunRef. */
export default function RunStreamPanel({ runId, title = "Agent run", onEnd, onClose, whenInterrupted }: Props) {
  const { events, state, retry } = useRunStream(runId, { onEnd });
  const tl = useMemo(() => buildTimeline(events), [events]);
  const { reportDown } = useHealth();

  useEffect(() => {
    if (tl.marketplaceDown) reportDown(tl.marketplaceDetail);
  }, [tl.marketplaceDown, tl.marketplaceDetail, reportDown]);

  let statusText = "Connecting to the run...";
  if (state === "live") statusText = tl.interrupted ? "Waiting for your decision" : "Running";
  if (state === "ended") statusText = tl.error ? "Run ended with an error" : "Run finished";
  if (state === "dropped") statusText = "Connection to the run was lost";

  return (
    <section className="card run-panel" aria-label={title} data-testid="run-stream-panel">
      <div className="run-panel__head">
        <div>
          <h3>{title}</h3>
          <p className={`run-panel__status run-panel__status--${state}`} role="status" aria-live="polite">
            {(state === "live" || state === "connecting") && <span className="spinner" aria-hidden="true" />}
            {statusText}
          </p>
        </div>
        <div className="row">
          <Link className="btn btn--ghost btn--sm" to={`/runs/${encodeURIComponent(runId)}`}>
            Open run viewer
          </Link>
          {onClose && (
            <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>
              Dismiss
            </button>
          )}
        </div>
      </div>
      <RunTimeline events={events} live={state !== "ended"} />
      {tl.notes.map((n) => (
        <p key={n.id} className={n.tone === "error" ? "inline-error" : "note note--warn"} role={n.tone === "error" ? "alert" : undefined}>
          {n.text}
        </p>
      ))}
      {state === "dropped" && (
        <p>
          <button type="button" className="btn btn--sm" onClick={retry}>
            Reconnect
          </button>
        </p>
      )}
      {tl.interrupted && whenInterrupted}
    </section>
  );
}
