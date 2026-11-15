import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { endpoints } from "../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../lib/hooks";
import { budgetText, money, num, timeAgo } from "../../lib/format";
import type { JobCard } from "../../lib/types";
import { EmptyState, ErrorState, InlineError, PageHeader, SkeletonCards } from "../../components/States";
import RiskBadge, { ActionChip, StatusPill } from "../../components/RiskBadge";
import SkipControl from "../../components/SkipControl";
import { useRunPanels } from "../../components/RunPanels";
import { useToast } from "../../lib/toast";

const STATUSES = ["new", "analyzed", "approval_pending", "drafted", "submitted", "skipped"];

function runIdsFrom(r: Record<string, unknown>): string[] {
  const q = r.queued;
  if (!Array.isArray(q)) return [];
  return q.map((x) => (typeof x === "string" ? x : ((x as { run_id?: string })?.run_id ?? ""))).filter(Boolean);
}

export default function InboxPage() {
  useDocumentTitle("Inbox");
  const toast = useToast();
  const [status, setStatus] = useState("");
  const [action, setAction] = useState("");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");

  const jobs = useAsync(() => endpoints.jobs({ status, action, q: query }), [status, action, query]);
  const panels = useRunPanels(() => void jobs.reload());

  const scout = useAction(async () => {
    const r = await endpoints.scout();
    const ids = runIdsFrom(r);
    const dups = Array.isArray(r.duplicates) ? r.duplicates.length : typeof r.duplicates === "number" ? r.duplicates : 0;
    ids.forEach((id, i) => panels.add(id, ids.length > 1 ? `Scouting (${i + 1} of ${ids.length})` : "Scouting for new jobs"));
    toast.ok(ids.length ? `Scout started: ${ids.length} run${ids.length > 1 ? "s" : ""}${dups ? `, ${dups} duplicates skipped` : ""}.` : dups ? `No new jobs. ${dups} duplicates skipped.` : "Scout finished with nothing new.");
    if (!ids.length) void jobs.reload();
  });

  const analyze = useAction(async (j: JobCard) => {
    const ref = await endpoints.analyze(j.job_id);
    panels.add(ref.run_id, `Analysing: ${j.title}`);
  });

  const ranked = useMemo(() => [...(jobs.data ?? [])].sort((a, b) => (b.fit_score ?? -1) - (a.fit_score ?? -1)), [jobs.data]);
  const statusOptions = useMemo(() => Array.from(new Set([...STATUSES, ...(jobs.data ?? []).map((j) => j.status)])), [jobs.data]);
  const filtered = !!(status || action || query);

  return (
    <>
      <PageHeader title="Job inbox" sub="Jobs ranked by how well they fit you.">
        <button type="button" className="btn btn--primary" disabled={scout.busy} onClick={() => void scout.call()}>
          {scout.busy ? "Scouting..." : "Scout now"}
        </button>
      </PageHeader>
      <InlineError message={scout.error ?? analyze.error} />
      {panels.panels}

      <form
        className="filters"
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(q.trim());
        }}
      >
        <div className="field">
          <label htmlFor="f-q">Search</label>
          <input id="f-q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Title or keyword" />
        </div>
        <div className="field">
          <label htmlFor="f-status">Status</label>
          <select id="f-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-action">Recommended action</label>
          <select id="f-action" value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">All</option>
            <option value="bid">Bid</option>
            <option value="watch">Watch</option>
            <option value="skip">Skip</option>
          </select>
        </div>
        <button type="submit" className="btn">
          Search
        </button>
      </form>

      {jobs.loading && <SkeletonCards count={4} />}
      {jobs.error && <ErrorState message={jobs.error} onRetry={jobs.reload} />}
      {!jobs.loading && !jobs.error && ranked.length === 0 && (
        <EmptyState
          title={filtered ? "No jobs match these filters" : "No jobs yet"}
          action={
            filtered ? (
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setStatus("");
                  setAction("");
                  setQ("");
                  setQuery("");
                }}
              >
                Clear filters
              </button>
            ) : (
              <button type="button" className="btn btn--primary" onClick={() => void scout.call()} disabled={scout.busy}>
                Scout now
              </button>
            )
          }
        >
          {filtered ? "Try a different status, action or keyword." : "Choose Scout now and GigBid searches the marketplace using your saved searches, scores each job for fit and risk, and lists the best ones here. Add or edit searches in Settings."}
        </EmptyState>
      )}

      <ul className="job-list" aria-label="Jobs">
        {ranked.map((j) => (
          <li key={j.job_id} className="card job">
            <div className="job__main">
              <div className="job__title-row">
                <h2 className="h3 job__title">
                  <Link to={`/jobs/${encodeURIComponent(j.job_id)}`}>{j.title}</Link>
                </h2>
                <StatusPill status={j.status} />
              </div>
              <p className="muted small">
                {[j.category, budgetText(j), j.posted_at ? `posted ${timeAgo(j.posted_at)}` : ""].filter(Boolean).join(" | ")}
              </p>
              <div className="job__badges">
                <ActionChip action={j.action} />
                <RiskBadge score={j.risk_score} flags={j.risk_flags} injection={j.injection_detected} />
              </div>
            </div>
            <dl className="job__stats">
              <div>
                <dt>Fit</dt>
                <dd>{j.fit_score != null ? Math.round(j.fit_score <= 1 ? j.fit_score * 100 : j.fit_score) : "-"}</dd>
              </div>
              <div>
                <dt>Bid</dt>
                <dd>{j.price ? money(j.price.amount) : "-"}</dd>
              </div>
              <div>
                <dt>Connects</dt>
                <dd>{num(j.connects_cost ?? j.price?.connects_cost)}</dd>
              </div>
            </dl>
            <div className="job__actions">
              <Link className="btn btn--sm" to={`/jobs/${encodeURIComponent(j.job_id)}`}>
                Open
              </Link>
              <button type="button" className="btn btn--sm" disabled={analyze.busy} onClick={() => void analyze.call(j)}>
                Analyze
              </button>
              {j.thread_id && j.status === "approval_pending" && (
                <Link className="btn btn--sm btn--primary" to={`/studio/${encodeURIComponent(j.thread_id)}`}>
                  Open in studio
                </Link>
              )}
              {j.status !== "skipped" && <SkipControl jobId={j.job_id} onSkipped={() => void jobs.reload()} />}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
