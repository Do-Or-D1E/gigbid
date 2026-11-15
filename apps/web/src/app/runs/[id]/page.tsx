import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { endpoints } from "../../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../../lib/hooks";
import { dateTime, money, num, seconds } from "../../../lib/format";
import type { AnyRec } from "../../../lib/types";
import type { StreamEvent } from "../../../lib/timeline";
import { tokenTotal } from "../../../lib/timeline";
import { EmptyState, ErrorState, InlineError, PageHeader, Skeleton } from "../../../components/States";
import RunTimeline from "../../../components/RunTimeline";
import RunStreamPanel from "../../../components/RunStreamPanel";
import { StatusPill } from "../../../components/RiskBadge";
import Kv from "../../../components/Kv";

const ACTIVE = ["queued", "running", "pending", "started", "in_progress"];

function pick(r: AnyRec, ...keys: string[]): unknown {
  for (const k of keys) if (r[k] !== undefined && r[k] !== null) return r[k];
  return undefined;
}

export default function RunPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  useDocumentTitle("Run");
  const detail = useAsync(() => endpoints.run(id), [id]);
  const history = useAsync(() => endpoints.runHistory(id), [id]);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  const share = useAction(async () => {
    const r = await endpoints.share(id);
    setShareUrl(r.url);
  });
  const replay = useAction(async (checkpoint: string) => {
    const ref = await endpoints.replay(id, checkpoint);
    nav(`/runs/${encodeURIComponent(ref.run_id)}`);
  });

  if (detail.loading) return <Skeleton lines={8} height={22} />;
  if (detail.error || !detail.data) return <ErrorState message={detail.error ?? "Run not found."} onRetry={detail.reload} />;

  const r = detail.data;
  const active = ACTIVE.includes(r.status.toLowerCase());
  const events = (r.events ?? []) as unknown as StreamEvent[];
  const perNode = (r.per_node ?? []) as AnyRec[];
  const spans = r.spans ?? [];
  const traceUrl = r.trace_url ?? shareUrl;
  const hasLink = !!traceUrl && /^https?:/i.test(traceUrl);

  return (
    <>
      <p className="crumb">
        <Link to="/runs">All runs</Link>
      </p>
      <PageHeader title={`Run ${r.kind.replace(/_/g, " ")}`} sub={<span className="mono">{r.run_id}</span>}>
        <StatusPill status={r.status} />
        {hasLink ? (
          <a className="btn" href={traceUrl!} target="_blank" rel="noreferrer">
            Open full trace
          </a>
        ) : (
          <button type="button" className="btn" disabled={share.busy} onClick={() => void share.call()}>
            Create public trace link
          </button>
        )}
      </PageHeader>
      <InlineError message={share.error ?? replay.error} />
      {shareUrl && !/^https?:/i.test(shareUrl) && (
        <p className="note">
          Trace link: <a href={shareUrl}>{shareUrl}</a>
        </p>
      )}

      <div className="grid grid--2">
        <section className="card" aria-labelledby="h-sum">
          <h2 id="h-sum" className="h3">
            Summary
          </h2>
          <dl className="kv kv--tight">
            <div>
              <dt>Started</dt>
              <dd>{dateTime(r.created_at)}</dd>
            </div>
            <div>
              <dt>Finished</dt>
              <dd>{dateTime(r.finished_at)}</dd>
            </div>
            <div>
              <dt>Thread</dt>
              <dd className="mono small">{r.thread_id}</dd>
            </div>
            {r.job_id && (
              <div>
                <dt>Job</dt>
                <dd>
                  <Link to={`/jobs/${encodeURIComponent(r.job_id)}`}>Open job</Link>
                </dd>
              </div>
            )}
          </dl>
          {r.error && (
            <p className="inline-error" role="alert">
              {r.error}
            </p>
          )}
          {r.metrics && Object.keys(r.metrics).length > 0 && (
            <>
              <h3 className="h4">Metrics</h3>
              <Kv data={r.metrics as AnyRec} />
            </>
          )}
        </section>

        <section className="card" aria-labelledby="h-tl">
          <h2 id="h-tl" className="h3">
            Steps
          </h2>
          {active ? <RunStreamPanel runId={id} title="Live run" onEnd={() => void detail.reload()} /> : <RunTimeline events={events} />}
        </section>
      </div>

      <section className="card" aria-labelledby="h-pn">
        <h2 id="h-pn" className="h3">
          Cost and time per node
        </h2>
        {perNode.length === 0 ? (
          <p className="muted">No per-node numbers were recorded.</p>
        ) : (
          <div className="table-wrap">
            <table className="table" data-testid="per-node">
              <thead>
                <tr>
                  <th scope="col">Node</th>
                  <th scope="col" className="num">LLM calls</th>
                  <th scope="col" className="num">Tool calls</th>
                  <th scope="col" className="num">Tokens</th>
                  <th scope="col" className="num">Cost</th>
                  <th scope="col" className="num">List cost</th>
                  <th scope="col" className="num">Latency</th>
                </tr>
              </thead>
              <tbody>
                {perNode.map((n, i) => (
                  <tr key={i}>
                    <th scope="row">{String(pick(n, "node", "name") ?? "-")}</th>
                    <td className="num">{num(pick(n, "llm_calls") as number)}</td>
                    <td className="num">{num(pick(n, "tool_calls") as number)}</td>
                    <td className="num">{num(tokenTotal(pick(n, "tokens", "total_tokens")) ?? ((Number(n.input_tokens) || 0) + (Number(n.output_tokens) || 0) || undefined))}</td>
                    <td className="num">{money(pick(n, "usd") as number, 4)}</td>
                    <td className="num">{money(pick(n, "list_usd") as number, 4)}</td>
                    <td className="num">{seconds(pick(n, "latency_s", "latency") as number)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="h-spans">
        <h2 id="h-spans" className="h3">
          Spans
        </h2>
        {spans.length === 0 ? (
          <p className="muted">No spans were recorded.</p>
        ) : (
          <div className="table-wrap">
            <table className="table" data-testid="spans">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Node</th>
                  <th scope="col">Model</th>
                  <th scope="col" className="num">In / out tokens</th>
                  <th scope="col" className="num">Cost</th>
                  <th scope="col" className="num">Latency</th>
                </tr>
              </thead>
              <tbody>
                {spans.map((s, i) => (
                  <tr key={i} className={s.error ? "row--error" : undefined}>
                    <th scope="row">
                      {s.name}
                      {s.error && <span className="inline-error"> {s.error}</span>}
                    </th>
                    <td>{s.kind}</td>
                    <td>{s.node ?? "-"}</td>
                    <td>{s.model ?? "-"}</td>
                    <td className="num">
                      {num(s.input_tokens)} / {num(s.output_tokens)}
                    </td>
                    <td className="num">{money(s.usd, 4)}</td>
                    <td className="num">{seconds(s.latency_s)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="h-hist">
        <h2 id="h-hist" className="h3">
          Checkpoint history
        </h2>
        {history.loading && <Skeleton lines={3} />}
        {history.error && <ErrorState title="Could not load history" message={history.error} onRetry={history.reload} />}
        {history.data && history.data.length === 0 && <EmptyState title="No checkpoints">This run did not save any checkpoints.</EmptyState>}
        {history.data && history.data.length > 0 && (
          <ol className="checkpoints">
            {history.data.map((c) => (
              <li key={c.checkpoint_id}>
                <div>
                  <span className="mono small">{c.checkpoint_id.slice(0, 12)}</span> <StatusPill status={c.status} />{" "}
                  <span className="muted small">{dateTime(c.created_at)}</span>
                  {c.next.length > 0 && <span className="muted small"> next: {c.next.join(", ")}</span>}
                </div>
                <button type="button" className="btn btn--sm" disabled={replay.busy} onClick={() => void replay.call(c.checkpoint_id)}>
                  Replay from here
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}
