import { useState } from "react";
import { Link } from "react-router-dom";
import { endpoints } from "../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../lib/hooks";
import { money, num, timeAgo } from "../../lib/format";
import { ErrorState, InlineError, PageHeader, Skeleton } from "../../components/States";
import { useToast } from "../../lib/toast";

const COLUMNS: { key: string; label: string }[] = [
  { key: "drafted", label: "Drafted" },
  { key: "submitted", label: "Submitted" },
  { key: "viewed", label: "Viewed" },
  { key: "replied", label: "Replied" },
  { key: "interview", label: "Interview" },
  { key: "hired", label: "Hired" },
  { key: "lost", label: "Lost" },
];
export const PIPELINE_REFRESH_MS = 30000;

export default function PipelinePage() {
  useDocumentTitle("Pipeline");
  const toast = useToast();
  const board = useAsync(() => endpoints.pipeline(), [], { intervalMs: PIPELINE_REFRESH_MS });
  const [syncedAt, setSyncedAt] = useState<Date | null>(null);
  const sync = useAction(async () => {
    await endpoints.syncPipeline();
    await board.reload();
    setSyncedAt(new Date());
    toast.ok("Pipeline synced.");
  });

  const cols = board.data?.columns ?? {};
  const known = new Set(COLUMNS.map((c) => c.key));
  const all = [...COLUMNS, ...Object.keys(cols).filter((k) => !known.has(k)).map((k) => ({ key: k, label: k.replace(/_/g, " ") }))];
  const total = Object.values(cols).reduce((n, l) => n + l.length, 0);

  return (
    <>
      <PageHeader title="Pipeline" sub="Every proposal from draft to outcome. Refreshes every 30 seconds.">
        <button type="button" className="btn" disabled={sync.busy} onClick={() => void sync.call()}>
          {sync.busy ? "Syncing..." : "Sync"}
        </button>
      </PageHeader>
      <InlineError message={sync.error} />
      {syncedAt && <p className="muted small">Last synced {syncedAt.toLocaleTimeString()}.</p>}
      {board.loading && <Skeleton lines={6} height={28} />}
      {board.error && <ErrorState message={board.error} onRetry={board.reload} />}
      {board.data && total === 0 && <p className="note">No proposals yet. Draft one from the inbox and it will appear here.</p>}
      {board.data && (
        <div className="board" role="region" aria-label="Pipeline board" tabIndex={0}>
          {all.map((col) => {
            const cards = cols[col.key] ?? [];
            return (
              <section key={col.key} className={`board__col board__col--${col.key}`} aria-labelledby={`col-${col.key}`}>
                <h2 id={`col-${col.key}`} className="board__head">
                  {col.label} <span className="count">{cards.length}</span>
                </h2>
                {cards.length === 0 && <p className="muted small board__empty">Nothing here.</p>}
                <ul className="board__list">
                  {cards.map((c) => {
                    const to = col.key === "drafted" && c.thread_id ? `/studio/${encodeURIComponent(c.thread_id)}` : c.job_id ? `/jobs/${encodeURIComponent(c.job_id)}` : null;
                    const body = (
                      <>
                        <span className="pcard__title">{c.title || c.job_id || c.proposal_id}</span>
                        <span className="pcard__meta">
                          {c.amount != null && money(c.amount)}
                          {c.connects != null && ` | ${num(c.connects)} Connects`}
                        </span>
                        {c.updated_at && <span className="pcard__time">{timeAgo(c.updated_at)}</span>}
                        {col.key === "drafted" && <span className="pcard__cta">Review in studio</span>}
                      </>
                    );
                    return (
                      <li key={c.proposal_id} className="pcard">
                        {to ? (
                          <Link to={to} className="pcard__link">
                            {body}
                          </Link>
                        ) : (
                          <div className="pcard__link">{body}</div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
