import { Link } from "react-router-dom";
import { endpoints } from "../../lib/endpoints";
import { useAsync, useDocumentTitle } from "../../lib/hooks";
import { dateTime } from "../../lib/format";
import { EmptyState, ErrorState, PageHeader, SkeletonCards } from "../../components/States";
import { StatusPill } from "../../components/RiskBadge";

export default function RunsPage() {
  useDocumentTitle("Runs");
  const runs = useAsync(() => endpoints.runs(50), []);
  return (
    <>
      <PageHeader title="Agent runs" sub="Every step GigBid took, with cost and timing." />
      {runs.loading && <SkeletonCards count={4} />}
      {runs.error && <ErrorState message={runs.error} onRetry={runs.reload} />}
      {runs.data && runs.data.length === 0 && <EmptyState title="No runs yet">Runs appear here after you scout, analyse or draft.</EmptyState>}
      <ul className="job-list">
        {(runs.data ?? []).map((r) => (
          <li key={r.run_id} className="card run-row">
            <div>
              <Link to={`/runs/${encodeURIComponent(r.run_id)}`} className="h4">
                {r.kind.replace(/_/g, " ")}
              </Link>{" "}
              <StatusPill status={r.status} />
              <p className="muted small mono">{r.run_id}</p>
            </div>
            <span className="muted small">{dateTime(r.created_at)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}
