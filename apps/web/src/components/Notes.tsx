import type { Compliance, Critique } from "../lib/types";
import { humanize } from "../lib/format";

/** Critic verdicts and issues, newest round first. Used on the job page. */
export function CritiqueList({ critiques }: { critiques: Critique[] }) {
  if (!critiques.length) return <p className="muted">The critic has not reviewed a draft yet.</p>;
  const sorted = [...critiques].sort((a, b) => (b.round ?? 0) - (a.round ?? 0));
  return (
    <ul className="notes">
      {sorted.map((c, i) => (
        <li key={i} className="note-card">
          <p>
            <strong>Critic{c.round != null ? `, round ${c.round}` : ""}:</strong> <span className={`pill pill--${c.verdict === "pass" || c.verdict === "approve" ? "done" : "waiting"}`}>{c.verdict}</span>
            {c.score != null && <span className="muted small"> score {c.score}</span>}
          </p>
          {(c.issues ?? []).length > 0 && (
            <ul className="plain-list">
              {c.issues!.map((is, j) => (
                <li key={j}>
                  <span className="tag">{humanize(is.kind)}</span> {is.detail}
                  {is.paragraph != null && <span className="muted small"> (paragraph {is.paragraph})</span>}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}

export function ComplianceNote({ compliance }: { compliance?: Compliance | null }) {
  if (!compliance) return <p className="muted">Compliance has not checked a draft yet.</p>;
  const ok = ["pass", "ok", "approve", "approved", "clean"].includes(compliance.verdict);
  return (
    <div className="note-card">
      <p>
        <strong>Compliance:</strong> <span className={`pill pill--${ok ? "done" : "error"}`}>{compliance.verdict}</span>
      </p>
      {compliance.reason && <p>{compliance.reason}</p>}
      {(compliance.violations ?? []).length > 0 && (
        <ul className="plain-list">
          {compliance.violations!.map((v, i) => (
            <li key={i}>
              <span className="tag">{v.rule_id}</span> {v.excerpt && <q>{v.excerpt}</q>} {v.action && <span className="muted small">Action: {v.action}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
