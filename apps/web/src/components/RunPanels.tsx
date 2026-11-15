import { useCallback, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import RunStreamPanel from "./RunStreamPanel";

const MAX_OPEN = 4;

/**
 * Keeps a list of runs started from a page and renders a live stream panel for each.
 * Any action that returns a RunRef should call `add` so the user sees progress right away.
 */
export function useRunPanels(onEnd?: () => void, whenInterrupted?: (runId: string) => ReactNode) {
  const [runs, setRuns] = useState<{ id: string; title: string }[]>([]);

  const add = useCallback((id: string, title: string) => {
    setRuns((r) => (r.some((x) => x.id === id) ? r : [{ id, title }, ...r]));
  }, []);
  const remove = useCallback((id: string) => setRuns((r) => r.filter((x) => x.id !== id)), []);

  const panels =
    runs.length === 0 ? null : (
      <div className="stack" aria-label="Live runs">
        {runs.slice(0, MAX_OPEN).map((r) => (
          <RunStreamPanel key={r.id} runId={r.id} title={r.title} onEnd={onEnd} onClose={() => remove(r.id)} whenInterrupted={whenInterrupted?.(r.id)} />
        ))}
        {runs.length > MAX_OPEN && (
          <p className="muted small">
            {runs.length - MAX_OPEN} more runs are queued:{" "}
            {runs.slice(MAX_OPEN).map((r) => (
              <Link key={r.id} to={`/runs/${r.id}`} className="inline-link">
                {r.id.slice(0, 8)}{" "}
              </Link>
            ))}
          </p>
        )}
      </div>
    );

  return { add, remove, panels, count: runs.length };
}
