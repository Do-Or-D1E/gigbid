import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { endpoints } from "../../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../../lib/hooks";
import { joinParagraphs, splitParagraphs } from "../../../lib/claims";
import { budgetText, money, pct } from "../../../lib/format";
import type { ProposalPayload } from "../../../lib/types";
import { EmptyState, ErrorState, PageHeader, Skeleton } from "../../../components/States";
import ApprovalPanel from "../../../components/ApprovalPanel";
import ProposalEditor from "../../../components/ProposalEditor";
import RunStreamPanel from "../../../components/RunStreamPanel";
import RiskBadge from "../../../components/RiskBadge";
import Kv from "../../../components/Kv";

type Action = "approve" | "edit" | "reject";

export default function StudioPage() {
  const { id = "" } = useParams();
  const approval = useAsync(() => endpoints.approval(id), [id]);
  const p = (approval.data?.payload ?? {}) as ProposalPayload;
  useDocumentTitle(p.job?.title ? `Studio: ${p.job.title}` : "Proposal studio");

  const original = p.draft?.cover_letter ?? "";
  const originalAnswers = p.draft?.screening_answers;
  const [paragraphs, setParagraphs] = useState<string[]>([""]);
  const [answers, setAnswers] = useState<{ question: string; answer: string }[]>([]);
  const [run, setRun] = useState<{ id: string; action: Action } | null>(null);
  const [finished, setFinished] = useState(false);

  // Reset the editor whenever a new draft version arrives (initial load, or after an edit was re-checked).
  const draftKey = `${approval.data?.thread_id}:${p.draft?.version ?? 0}:${approval.data?.status}:${original.length}`;
  useEffect(() => {
    setParagraphs(splitParagraphs(original));
    setAnswers((originalAnswers ?? []).map((a) => ({ ...a })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftKey]);

  const letterDirty = joinParagraphs(paragraphs) !== joinParagraphs(splitParagraphs(original));
  const answersDirty = JSON.stringify(answers) !== JSON.stringify(originalAnswers ?? []);
  const dirty = letterDirty || answersDirty;

  const decide = useAction(async (action: Action, reason?: string) => {
    const body =
      action === "edit"
        ? { action, edited_cover_letter: joinParagraphs(paragraphs), edited_answers: answersDirty ? answers : undefined }
        : action === "reject"
          ? { action, reason }
          : { action };
    const ref = await endpoints.decide(id, body);
    setFinished(false);
    setRun({ id: ref.run_id, action });
  });

  const runDetail = useAsync(
    async () => (run && finished ? endpoints.run(run.id) : undefined),
    [run?.id, finished],
  );

  const status = approval.data?.status ?? "";
  const pending = status === "pending";
  const claims = useMemo(() => p.claims ?? [], [p.claims]);

  if (approval.data?.kind === "message") return <Navigate to={`/messages/${encodeURIComponent(id)}`} replace />;
  if (approval.loading) return <Skeleton lines={8} height={22} />;
  if (approval.error || !approval.data) return <ErrorState message={approval.error ?? "Approval not found."} onRetry={approval.reload} />;

  const job = p.job;
  const report = p.claim_report;
  const decisionText =
    status === "approved" || status === "sent" || status === "submitted"
      ? "Approved. The proposal was submitted."
      : status === "rejected"
        ? `Rejected${approval.data.decision?.reason ? `: ${String(approval.data.decision.reason)}` : "."}`
        : `Status: ${status.replace(/_/g, " ")}.`;

  const onRunEnd = () => {
    setFinished(true);
    void approval.reload();
  };

  return (
    <>
      <p className="crumb">
        <Link to="/inbox">Inbox</Link>
        {job?.job_id && (
          <>
            {" / "}
            <Link to={`/jobs/${encodeURIComponent(job.job_id)}`}>Job</Link>
          </>
        )}
      </p>
      <PageHeader title={job?.title ?? "Proposal"} sub={job ? [job.category, budgetText(job)].filter(Boolean).join(" | ") : undefined}>
        <span className={`pill pill--${pending ? "waiting" : status === "rejected" ? "error" : "done"}`}>{pending ? "Waiting for your decision" : status.replace(/_/g, " ")}</span>
      </PageHeader>

      {run && (
        <RunStreamPanel
          runId={run.id}
          title={run.action === "approve" ? "Submitting your proposal" : run.action === "edit" ? "Re-checking your edit" : "Recording your rejection"}
          onEnd={onRunEnd}
          onClose={() => setRun(null)}
        />
      )}
      {run && finished && run.action === "approve" && (
        <section className="card result" aria-labelledby="result-h" data-testid="submit-result">
          <h2 id="result-h" className="h3">
            {status === "pending" ? "Submission needs another look" : "Submitted"}
          </h2>
          {runDetail.loading ? <Skeleton lines={2} /> : null}
          {runDetail.data?.error && <p className="inline-error">{runDetail.data.error}</p>}
          {runDetail.data && (
            <>
              <p>
                Run status: <strong>{runDetail.data.status}</strong>
              </p>
              <Kv data={runDetail.data.metrics as Record<string, unknown>} />
            </>
          )}
          <p>
            <Link className="btn btn--sm" to="/pipeline">
              See it in the pipeline
            </Link>{" "}
            <Link className="btn btn--sm btn--ghost" to={`/runs/${encodeURIComponent(run.id)}`}>
              Open run viewer
            </Link>
          </p>
        </section>
      )}
      {run && finished && run.action === "edit" && pending && (
        <p className="note" role="status">
          Your edit was re-checked by Compliance. Review the new version below before approving.
        </p>
      )}
      {run && finished && run.action === "reject" && !pending && (
        <p className="note" role="status">
          Rejected. GigBid will use your reason to improve future suggestions.
        </p>
      )}

      <div className="studio">
        <div className="studio__main">
          <section className="card card--flat context" aria-label="Job context">
            <div className="row row--wrap">
              <RiskBadge score={p.risk?.risk_score} flags={p.risk?.flags} scam={p.risk?.is_scam} />
              {p.fit?.fit_score != null && <span className="chip chip--neutral">Fit {Math.round(p.fit.fit_score <= 1 ? p.fit.fit_score * 100 : p.fit.fit_score)}</span>}
              {p.price?.amount != null && (
                <span className="chip chip--neutral">
                  Bid {money(p.price.amount as number)} ({String(p.price.bid_type ?? "")})
                </span>
              )}
              {p.price?.win_probability != null && <span className="chip chip--neutral">Win chance {pct(p.price.win_probability as number)}</span>}
              {p.decision?.action && <span className={`chip chip--${p.decision.action}`}>Recommended: {p.decision.action}</span>}
            </div>
            {report && (
              <p className="muted small">
                Unsupported claims: {report.unsupported_before_first_draft ?? report.unsupported_before ?? 0} in the first draft, {report.unsupported_after ?? 0} now.
                {report.rewritten ? ` ${report.rewritten} rewritten.` : ""}
              </p>
            )}
          </section>

          {original ? (
            <ProposalEditor
              threadId={id}
              paragraphs={paragraphs}
              claims={claims}
              critiques={p.critiques ?? []}
              compliance={p.compliance}
              readOnly={!pending}
              onChange={(i, t) => setParagraphs((ps) => ps.map((x, j) => (j === i ? t : x)))}
              answers={answers}
              onAnswerChange={(i, t) => setAnswers((as) => as.map((a, j) => (j === i ? { ...a, answer: t } : a)))}
            />
          ) : (
            <EmptyState title="This approval has no draft">The agent has not produced a cover letter for this job yet.</EmptyState>
          )}
        </div>

        <div className="studio__side">
          <ApprovalPanel
            preview={p.preview}
            pending={pending}
            dirty={dirty}
            busy={decide.busy}
            error={decide.error}
            decisionText={decisionText}
            onApprove={() => void decide.call("approve")}
            onEdit={() => void decide.call("edit")}
            onReject={(reason) => void decide.call("reject", reason)}
          />
        </div>
      </div>
    </>
  );
}
