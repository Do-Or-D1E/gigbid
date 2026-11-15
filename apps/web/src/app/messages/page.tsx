import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { endpoints } from "../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../lib/hooks";
import { dateTime, timeAgo } from "../../lib/format";
import type { MessagePayload } from "../../lib/types";
import { EmptyState, ErrorState, InlineError, PageHeader, Skeleton, SkeletonCards } from "../../components/States";
import ApprovalPanel from "../../components/ApprovalPanel";
import RunStreamPanel from "../../components/RunStreamPanel";
import { ComplianceNote } from "../../components/Notes";

function isScam(intent?: string): boolean {
  return !!intent && /scam|fraud|phish/i.test(intent);
}

export default function MessagesPage() {
  useDocumentTitle("Messages");
  const { threadId } = useParams();
  const threads = useAsync(() => endpoints.threads(), [], { intervalMs: 30000 });
  const unavailable = threads.status === 503;

  return (
    <>
      <PageHeader title="Messages" sub="Client replies. GigBid suggests an answer and you approve it before it is sent." />
      <div className={`messages${threadId ? " messages--open" : ""}`}>
        <section className="messages__list" aria-label="Threads">
          {threads.loading && <SkeletonCards count={3} />}
          {threads.error && (
            <ErrorState
              title={unavailable ? "Messages are unavailable" : "Could not load messages"}
              message={unavailable ? "The marketplace is not responding. GigBid will keep trying and this list will update on its own." : threads.error}
              onRetry={threads.reload}
            />
          )}
          {threads.data && threads.data.length === 0 && <EmptyState title="No conversations yet">When a client replies to one of your proposals, the conversation shows up here.</EmptyState>}
          <ul className="thread-list">
            {(threads.data ?? []).map((t) => (
              <li key={t.thread_id}>
                <Link to={`/messages/${encodeURIComponent(t.thread_id)}`} className={`thread-item${t.thread_id === threadId ? " is-active" : ""}`} aria-current={t.thread_id === threadId ? "page" : undefined}>
                  <span className="thread-item__title">{t.title || t.job_id || t.thread_id}</span>
                  <span className="thread-item__last">{t.last_message}</span>
                  <span className="thread-item__meta">
                    {t.updated_at && <span className="muted small">{timeAgo(t.updated_at)}</span>}
                    {t.pending_reply && <span className="pill pill--waiting">Reply to review</span>}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
        <section className="messages__thread" aria-label="Conversation">
          {threadId ? (
            <ThreadView key={threadId} id={threadId} onChanged={() => void threads.reload()} />
          ) : (
            <EmptyState title="Choose a conversation">Select a thread to read it and review GigBid&apos;s suggested reply.</EmptyState>
          )}
        </section>
      </div>
    </>
  );
}

function ThreadView({ id, onChanged }: { id: string; onChanged: () => void }) {
  const thread = useAsync(() => endpoints.thread(id), [id]);
  const [runId, setRunId] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string>("");
  const [replyText, setReplyText] = useState("");

  const approval = thread.data?.approval ?? null;
  const p = (approval?.payload ?? {}) as MessagePayload;
  const pending = approval?.status === "pending";
  const original = p.reply?.text ?? "";
  useDocumentTitle(thread.data ? "Conversation" : "Messages");

  useEffect(() => setReplyText(original), [original, approval?.created_at]);
  const dirty = replyText !== original;

  const suggest = useAction(async () => {
    const ref = await endpoints.suggest(id);
    setLastAction("suggest");
    setRunId(ref.run_id);
  });
  const decide = useAction(async (action: "approve" | "edit" | "reject", reason?: string) => {
    const body = action === "edit" ? { action, edited_cover_letter: replyText } : action === "reject" ? { action, reason } : { action };
    const ref = await endpoints.decide(approval?.thread_id ?? id, body);
    setLastAction(action);
    setRunId(ref.run_id);
  });

  if (thread.loading) return <Skeleton lines={6} height={22} />;
  if (thread.error || !thread.data) {
    return (
      <ErrorState
        title={thread.status === 503 ? "This conversation is unavailable" : "Could not load this conversation"}
        message={thread.status === 503 ? "The marketplace is not responding. Try again in a moment." : (thread.error ?? "Not found.")}
        onRetry={thread.reload}
      />
    );
  }
  const d = thread.data;
  const scam = isScam(p.intent?.intent) || (p.injection_hits ?? []).length > 0;
  const slotList = (p.slots ?? []).length ? p.slots!.map((s) => s.label || `${dateTime(s.start)} to ${dateTime(s.end)}`) : (p.reply?.proposed_slots ?? []);

  const onEnd = () => {
    void thread.reload();
    onChanged();
  };

  return (
    <div className="stack">
      <p className="crumb crumb--back">
        <Link to="/messages">All conversations</Link>
      </p>
      <div className="row row--between">
        <h2 className="h3">Conversation</h2>
        <button type="button" className="btn" disabled={suggest.busy} onClick={() => void suggest.call()}>
          Suggest reply
        </button>
      </div>
      <InlineError message={suggest.error} />
      {runId && (
        <RunStreamPanel
          runId={runId}
          title={lastAction === "suggest" ? "Drafting a reply" : lastAction === "approve" ? "Sending your reply" : lastAction === "edit" ? "Re-checking your edit" : "Recording your decision"}
          onEnd={onEnd}
          onClose={() => setRunId(null)}
        />
      )}

      <ol className="chat" aria-label="Messages">
        {d.messages.length === 0 && <li className="muted">No messages in this thread yet.</li>}
        {d.messages.map((m, i) => (
          <li key={i} className={`bubble bubble--${/client/i.test(m.sender) ? "client" : "me"}`}>
            <span className="bubble__who">
              {m.sender} {m.at && <span className="muted small">{dateTime(m.at)}</span>}
            </span>
            <span className="bubble__text">{m.text}</span>
          </li>
        ))}
      </ol>

      {approval && (
        <section className="card" aria-labelledby="reply-h" data-testid="reply-approval">
          <h3 id="reply-h" className="h3">
            Suggested reply
          </h3>
          {p.intent && (
            <div className={`intent${isScam(p.intent.intent) ? " intent--scam" : ""}`} role={isScam(p.intent.intent) ? "alert" : "note"}>
              <strong>{isScam(p.intent.intent) ? "Scam signal: " : "Client intent: "}</strong>
              {p.intent.intent.replace(/_/g, " ")}
              {p.intent.confidence != null && <span className="muted small"> ({Math.round(p.intent.confidence <= 1 ? p.intent.confidence * 100 : p.intent.confidence)}% sure)</span>}
              {p.intent.summary && <p>{p.intent.summary}</p>}
              {isScam(p.intent.intent) && <p>Do not share personal details, move to another platform, or pay anything. Rejecting is the safe choice.</p>}
            </div>
          )}
          {scam && (p.injection_hits ?? []).length > 0 && (
            <div className="note note--warn">
              <strong>The message contains instructions aimed at the AI. They were ignored.</strong>
              <ul className="plain-list">
                {p.injection_hits!.map((h, i) => (
                  <li key={i}>
                    <q>{h}</q>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="grid grid--approval">
            <div>
              <div className="field">
                <label htmlFor="reply-text">Reply</label>
                <textarea id="reply-text" rows={7} value={replyText} readOnly={!pending} onChange={(e) => setReplyText(e.target.value)} />
              </div>
              {slotList.length > 0 && (
                <div>
                  <h4 className="h4">Proposed interview slots</h4>
                  <ul className="slots" aria-label="Proposed interview slots">
                    {slotList.map((s, i) => (
                      <li key={i} className="slot">
                        {s}
                      </li>
                    ))}
                  </ul>
                  {p.reply?.create_hold && <p className="muted small">GigBid will place a calendar hold for the first slot once you approve.</p>}
                </div>
              )}
              <ComplianceNote compliance={p.compliance} />
            </div>
            <ApprovalPanel
              kindLabel="reply"
              preview={p.preview}
              pending={pending}
              dirty={dirty}
              busy={decide.busy}
              error={decide.error}
              decisionText={`Status: ${(approval.status ?? "").replace(/_/g, " ")}.`}
              onApprove={() => void decide.call("approve")}
              onEdit={() => void decide.call("edit")}
              onReject={(r) => void decide.call("reject", r)}
            />
          </div>
        </section>
      )}
      {!approval && d.messages.length > 0 && <p className="muted">No reply is waiting for review. Choose Suggest reply to draft one.</p>}
    </div>
  );
}
