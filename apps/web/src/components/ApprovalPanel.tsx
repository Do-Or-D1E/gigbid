import { useState } from "react";
import type { Preview } from "../lib/types";
import { num } from "../lib/format";

interface Props {
  preview?: Preview;
  /** false once a decision was made */
  pending: boolean;
  /** true when the user changed the draft and has not saved the edit yet */
  dirty: boolean;
  busy: boolean;
  error?: string | null;
  kindLabel?: string;
  onApprove: () => void;
  onEdit: () => void;
  onReject: (reason: string) => void;
  decisionText?: string;
}

/** The human gate. Nothing is sent until Approve is pressed here. */
export default function ApprovalPanel({ preview, pending, dirty, busy, error, kindLabel = "proposal", onApprove, onEdit, onReject, decisionText }: Props) {
  const [reason, setReason] = useState("");
  const after = preview?.balance_after;
  const overBudget = after !== undefined && after < 0;
  const hasPayload = preview?.payload !== undefined && preview?.payload !== null;

  return (
    <aside className="card approval" aria-label="Approval">
      <h2 className="h3">Review before sending</h2>
      <p className="muted small">GigBid never sends a {kindLabel} without your approval.</p>

      <section aria-label="Send preview" className="approval__preview">
        <h3 className="h4">What will be sent</h3>
        {hasPayload ? (
          <pre className="payload" data-testid="preview-payload" tabIndex={0} aria-label="Exact payload that will be sent">
            {typeof preview!.payload === "string" ? (preview!.payload as string) : JSON.stringify(preview!.payload, null, 2)}
          </pre>
        ) : (
          <p className="muted">No preview available.</p>
        )}
        <dl className="kv kv--tight" data-testid="connects">
          <div>
            <dt>Connects cost</dt>
            <dd>{num(preview?.connects_cost)}</dd>
          </div>
          <div>
            <dt>Balance</dt>
            <dd>{num(preview?.connects_balance)}</dd>
          </div>
          <div>
            <dt>Balance after</dt>
            <dd className={overBudget ? "text-bad" : undefined}>{num(after)}</dd>
          </div>
        </dl>
        {overBudget && <p className="inline-error">Not enough Connects to send this.</p>}
        {(preview?.policy_warnings ?? []).length > 0 && (
          <ul className="warnings" aria-label="Policy warnings">
            {preview!.policy_warnings!.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        )}
      </section>

      {pending ? (
        <>
          {dirty && <p className="note note--warn">You have unsaved changes. Save the edit so Compliance can re-check it. Approval sends the saved version.</p>}
          <div className="approval__actions">
            <button type="button" className="btn btn--primary" disabled={busy || dirty} onClick={onApprove}>
              Approve and send
            </button>
            <button type="button" className="btn" disabled={busy || !dirty} onClick={onEdit}>
              Save edit
            </button>
          </div>
          <div className="field">
            <label htmlFor="reject-reason">Reason for rejecting</label>
            <textarea id="reject-reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why should this not be sent?" />
          </div>
          <button type="button" className="btn btn--danger" disabled={busy || reason.trim().length === 0} onClick={() => onReject(reason.trim())}>
            Reject
          </button>
        </>
      ) : (
        <p className="note" role="status">
          {decisionText ?? "A decision was recorded for this item."}
        </p>
      )}
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
    </aside>
  );
}
