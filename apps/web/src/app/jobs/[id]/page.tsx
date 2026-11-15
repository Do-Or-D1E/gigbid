import { Link, useNavigate, useParams } from "react-router-dom";
import { endpoints } from "../../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../../lib/hooks";
import { asList, budgetText, dateTime, money, num, pct } from "../../../lib/format";
import type { AnyRec, ProposalPayload } from "../../../lib/types";
import { ErrorState, InlineError, PageHeader, Skeleton } from "../../../components/States";
import RiskBadge, { ActionChip, StatusPill } from "../../../components/RiskBadge";
import EvidenceHover from "../../../components/EvidenceHover";
import Kv from "../../../components/Kv";
import { ComplianceNote, CritiqueList } from "../../../components/Notes";
import SkipControl from "../../../components/SkipControl";
import { useRunPanels } from "../../../components/RunPanels";

export default function JobDetailPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const detail = useAsync(() => endpoints.job(id), [id]);
  useDocumentTitle(detail.data?.card.title ?? "Job");
  const panels = useRunPanels(() => void detail.reload());

  const analyze = useAction(async () => {
    const ref = await endpoints.analyze(id);
    panels.add(ref.run_id, "Analysing this job");
  });
  const draft = useAction(async () => {
    const ref = await endpoints.draft(id);
    panels.add(ref.run_id, "Drafting a proposal");
  });

  if (detail.loading) return <Skeleton lines={8} height={22} />;
  if (detail.error || !detail.data) return <ErrorState message={detail.error ?? "Job not found."} onRetry={detail.reload} />;

  const d = detail.data;
  const c = d.card;
  const job = d.job as AnyRec;
  const risk = (d.risk ?? {}) as NonNullable<ProposalPayload["risk"]>;
  const fit = (d.fit ?? {}) as NonNullable<ProposalPayload["fit"]>;
  const decision = (d.decision ?? {}) as NonNullable<ProposalPayload["decision"]>;
  const price = c.price;
  const report = d.claim_report as AnyRec | null | undefined;
  const reasons = [...asList(decision.reasons), ...asList(fit.reasons)];
  const description = typeof job.description === "string" ? job.description : typeof job.text === "string" ? job.text : "";
  const threadId = c.thread_id;

  return (
    <>
      <p className="crumb">
        <Link to="/inbox">Inbox</Link>
      </p>
      <PageHeader
        title={c.title}
        sub={[c.category, budgetText(c), c.posted_at ? `posted ${dateTime(c.posted_at)}` : ""].filter(Boolean).join(" | ")}
      >
        <button type="button" className="btn" disabled={analyze.busy} onClick={() => void analyze.call()}>
          Analyze
        </button>
        <button type="button" className="btn" disabled={draft.busy} onClick={() => void draft.call()} title="Draft a proposal even if GigBid recommends skipping">
          Draft anyway
        </button>
        {d.approval_pending && threadId && (
          <Link className="btn btn--primary" to={`/studio/${encodeURIComponent(threadId)}`}>
            Open in studio
          </Link>
        )}
        {c.status !== "skipped" && <SkipControl jobId={id} size="md" onSkipped={() => nav("/inbox")} />}
      </PageHeader>
      <InlineError message={analyze.error ?? draft.error} />
      {panels.panels}

      <div className="row row--wrap job-summary">
        <StatusPill status={c.status} />
        <ActionChip action={c.action} />
        <RiskBadge score={c.risk_score} flags={c.risk_flags} injection={c.injection_detected} scam={risk.is_scam} />
      </div>
      {d.attention && (
        <p className="note note--warn" role="note">
          {d.attention}
        </p>
      )}

      <div className="grid grid--2">
        <section className="card" aria-labelledby="h-job">
          <h2 id="h-job" className="h3">
            Job
          </h2>
          {description ? <p className="prose">{description}</p> : null}
          <Kv data={d.job_spec as AnyRec | null} />
          {!d.job_spec && <Kv data={job} skip={["description", "text", "title"]} />}
        </section>

        <section className="card" aria-labelledby="h-decision">
          <h2 id="h-decision" className="h3">
            Bid or skip
          </h2>
          <p>
            <ActionChip action={decision.action ?? c.action} /> {fit.fit_score != null && <span className="muted">Fit score {Math.round(fit.fit_score <= 1 ? fit.fit_score * 100 : fit.fit_score)}</span>}{" "}
            {fit.coverage != null && <span className="muted">Coverage {pct(fit.coverage)}</span>}
          </p>
          {reasons.length > 0 ? (
            <ul className="plain-list">
              {reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">No reasoning yet. Choose Analyze to score this job.</p>
          )}
          {(fit.missing ?? []).length > 0 && (
            <>
              <h3 className="h4">Not covered by your portfolio</h3>
              <ul className="plain-list">
                {fit.missing!.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="card" aria-labelledby="h-risk">
          <h2 id="h-risk" className="h3">
            Risk report
          </h2>
          {d.risk ? (
            <>
              <dl className="kv kv--tight">
                <div>
                  <dt>Risk score</dt>
                  <dd>{risk.risk_score != null ? num(risk.risk_score <= 1 ? risk.risk_score * 100 : risk.risk_score) : "-"}</dd>
                </div>
                <div>
                  <dt>Client quality</dt>
                  <dd>{risk.client_quality ?? "-"}</dd>
                </div>
                <div>
                  <dt>Scam</dt>
                  <dd className={risk.is_scam ? "text-bad" : undefined}>{risk.is_scam ? "Likely" : "No"}</dd>
                </div>
              </dl>
              {risk.summary && <p>{risk.summary}</p>}
              {(risk.flags ?? []).length > 0 && (
                <ul className="plain-list">
                  {risk.flags!.map((f, i) => (
                    <li key={i}>
                      <span className={`badge badge--flag badge--sev-${f.severity}`}>{f.kind.replace(/_/g, " ")}</span> {f.evidence}
                    </li>
                  ))}
                </ul>
              )}
              {(risk.injected_instructions ?? []).length > 0 && (
                <div className="note note--warn">
                  <strong>Instructions aimed at the AI were found and ignored:</strong>
                  <ul className="plain-list">
                    {risk.injected_instructions!.map((t, i) => (
                      <li key={i}>
                        <q>{t}</q>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className="muted">Not analysed yet.</p>
          )}
        </section>

        <section className="card" aria-labelledby="h-price">
          <h2 id="h-price" className="h3">
            Price and Connects
          </h2>
          {price ? (
            <>
              <dl className="kv kv--tight">
                <div>
                  <dt>Suggested bid</dt>
                  <dd>
                    {money(price.amount)} <span className="muted small">{price.bid_type}</span>
                  </dd>
                </div>
                <div>
                  <dt>Floor</dt>
                  <dd>{money(price.floor)}</dd>
                </div>
                <div>
                  <dt>Market p25 / p50 / p75</dt>
                  <dd>
                    {money(price.market_p25)} / {money(price.market_p50)} / {money(price.market_p75)}
                  </dd>
                </div>
                <div>
                  <dt>Connects</dt>
                  <dd>
                    {num(price.connects_cost)} ({money(price.connects_usd, 2)})
                  </dd>
                </div>
                <div>
                  <dt>Expected value</dt>
                  <dd>{money(price.expected_value_usd, 2)}</dd>
                </div>
                <div>
                  <dt>Win chance</dt>
                  <dd>{pct(price.win_probability)}</dd>
                </div>
              </dl>
              <p>
                <span className={`pill pill--${price.worth_it ? "done" : "waiting"}`}>{price.worth_it ? "Worth the Connects" : "Not worth the Connects"}</span>
              </p>
              {price.rationale && <p>{price.rationale}</p>}
            </>
          ) : (
            <p className="muted">No price suggestion yet.</p>
          )}
        </section>
      </div>

      <section className="card" aria-labelledby="h-matrix">
        <h2 id="h-matrix" className="h3">
          Requirements and evidence
        </h2>
        {(d.matrix ?? []).length === 0 ? (
          <p className="muted">No requirement matrix yet. Analyze the job to build one.</p>
        ) : (
          <table className="table table--stack" data-testid="matrix">
            <thead>
              <tr>
                <th scope="col">Requirement</th>
                <th scope="col">Match</th>
                <th scope="col">Evidence</th>
                <th scope="col">Why</th>
              </tr>
            </thead>
            <tbody>
              {d.matrix!.map((r, i) => (
                <tr key={i}>
                  <th scope="row" data-label="Requirement">
                    {r.requirement}
                  </th>
                  <td data-label="Match">
                    <span className={`pill pill--strength-${r.strength}`}>{r.strength.replace(/_/g, " ")}</span>
                  </td>
                  <td data-label="Evidence">
                    {r.evidence.length === 0 ? (
                      <span className="muted">None</span>
                    ) : (
                      <span className="evlist">
                        {r.evidence.map((e) => (
                          <EvidenceHover key={e.item_id} variant="link" evidence={[e]}>
                            {e.title}
                          </EvidenceHover>
                        ))}
                      </span>
                    )}
                  </td>
                  <td data-label="Why">{r.reason ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="grid grid--2">
        <section className="card" aria-labelledby="h-critic">
          <h2 id="h-critic" className="h3">
            Critic notes
          </h2>
          <CritiqueList critiques={(d.critiques ?? []) as never} />
        </section>
        <section className="card" aria-labelledby="h-comp">
          <h2 id="h-comp" className="h3">
            Compliance
          </h2>
          <ComplianceNote compliance={d.compliance as never} />
          {report && (
            <>
              <h3 className="h4">Claim check</h3>
              <Kv data={report} />
            </>
          )}
        </section>
      </div>

      <section className="card" aria-labelledby="h-runs">
        <h2 id="h-runs" className="h3">
          Runs
        </h2>
        {(d.runs ?? []).length === 0 ? (
          <p className="muted">No runs for this job yet.</p>
        ) : (
          <ul className="plain-list runs-list">
            {d.runs!.map((r) => (
              <li key={r.run_id}>
                <Link to={`/runs/${encodeURIComponent(r.run_id)}`}>{r.kind}</Link> <StatusPill status={r.status} /> <span className="muted small">{dateTime(r.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
