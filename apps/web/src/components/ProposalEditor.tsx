import { useMemo, useState } from "react";
import EvidenceHover, { STATUS_LABEL } from "./EvidenceHover";
import { InlineError } from "./States";
import { matchClaims, toSegments } from "../lib/claims";
import { endpoints } from "../lib/endpoints";
import { useAction } from "../lib/hooks";
import { humanize } from "../lib/format";
import type { Claim, Compliance, Critique } from "../lib/types";

interface Props {
  threadId: string;
  paragraphs: string[];
  claims: Claim[];
  critiques: Critique[];
  compliance?: Compliance;
  readOnly: boolean;
  onChange: (index: number, text: string) => void;
  answers: { question: string; answer: string }[];
  onAnswerChange: (index: number, text: string) => void;
}

interface Note {
  tone: "critic" | "compliance";
  text: string;
  kind?: string;
}

/** Paragraph numbering from the critic is not specified; accept 1-based when an issue points one past the last paragraph. */
function paragraphIndex(raw: number | null | undefined, count: number, oneBased: boolean): number | null {
  if (raw === null || raw === undefined) return null;
  const i = oneBased ? raw - 1 : raw;
  return i >= 0 && i < count ? i : null;
}

export default function ProposalEditor({ threadId, paragraphs, claims, critiques, compliance, readOnly, onChange, answers, onAnswerChange }: Props) {
  const [editing, setEditing] = useState<Record<number, boolean>>({});
  const { spans, unmatched } = useMemo(() => matchClaims(paragraphs, claims), [paragraphs, claims]);

  // Inline critic and compliance notes, keyed by the paragraph they refer to.
  const { byParagraph, general } = useMemo(() => {
    const by: Note[][] = paragraphs.map(() => []);
    const gen: Note[] = [];
    const latestRound = Math.max(0, ...critiques.map((c) => c.round ?? 0));
    const latest = critiques.filter((c) => (c.round ?? 0) === latestRound);
    const all = latest.flatMap((c) => c.issues ?? []);
    const oneBased = all.length > 0 && all.every((i) => i.paragraph != null && i.paragraph >= 1) && all.some((i) => i.paragraph === paragraphs.length);
    for (const c of latest) {
      for (const is of c.issues ?? []) {
        const idx = paragraphIndex(is.paragraph, paragraphs.length, oneBased);
        const note: Note = { tone: "critic", kind: is.kind, text: is.detail };
        if (idx === null) gen.push(note);
        else by[idx].push(note);
      }
    }
    for (const v of compliance?.violations ?? []) {
      const ex = (v.excerpt ?? "").toLowerCase().trim();
      const idx = ex ? paragraphs.findIndex((p) => p.toLowerCase().includes(ex)) : -1;
      const note: Note = { tone: "compliance", kind: v.rule_id, text: `${v.excerpt ? `"${v.excerpt}" ` : ""}${v.action ? `(${v.action})` : ""}`.trim() || v.rule_id };
      if (idx < 0) gen.push(note);
      else by[idx].push(note);
    }
    return { byParagraph: by, general: gen };
  }, [paragraphs, critiques, compliance]);

  const counts = useMemo(() => {
    const c = { supported: 0, partly_supported: 0, unsupported: 0 };
    claims.forEach((cl) => (c[cl.status] = (c[cl.status] ?? 0) + 1));
    return c;
  }, [claims]);

  return (
    <div className="editor">
      <ul className="legend" aria-label="Claim colours">
        {(["supported", "partly_supported", "unsupported"] as const).map((s) => (
          <li key={s}>
            <span className={`legend__swatch claim claim--${s}`} aria-hidden="true">
              Aa
            </span>
            {STATUS_LABEL[s]} ({counts[s]})
          </li>
        ))}
      </ul>

      {general.length > 0 && (
        <div className="note-card" role="note" aria-label="Review notes">
          <p>
            <strong>Review notes</strong>
          </p>
          <ul className="plain-list">
            {general.map((n, i) => (
              <li key={i}>
                <span className={`tag tag--${n.tone}`}>{n.tone === "critic" ? "Critic" : "Compliance"}</span> {n.kind && <span className="muted small">{humanize(n.kind)}: </span>}
                {n.text}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="letter" data-testid="letter">
        {paragraphs.map((text, i) => (
          <Paragraph
            key={i}
            index={i}
            threadId={threadId}
            text={text}
            segments={toSegments(text, spans[i])}
            notes={byParagraph[i]}
            editing={!!editing[i] && !readOnly}
            readOnly={readOnly}
            onToggle={() => setEditing((e) => ({ ...e, [i]: !e[i] }))}
            onChange={(t) => onChange(i, t)}
          />
        ))}
      </div>

      {unmatched.length > 0 && (
        <section className="card card--flat" aria-labelledby="unmatched-h" data-testid="unmatched-claims">
          <h3 id="unmatched-h" className="h4">
            Claims not found in the text above
          </h3>
          <p className="muted small">These claims were checked against your evidence but could not be located in the current wording.</p>
          <ul className="plain-list">
            {unmatched.map((c) => (
              <li key={c.claim_id}>
                <EvidenceHover status={c.status} evidence={c.evidence} note={c.note}>
                  {c.text}
                </EvidenceHover>
              </li>
            ))}
          </ul>
        </section>
      )}

      {answers.length > 0 && (
        <section className="card card--flat" aria-labelledby="answers-h">
          <h3 id="answers-h" className="h4">
            Screening answers
          </h3>
          {answers.map((a, i) => (
            <div className="field" key={i}>
              <label htmlFor={`ans-${i}`}>{a.question}</label>
              <textarea id={`ans-${i}`} rows={3} value={a.answer} readOnly={readOnly} onChange={(e) => onAnswerChange(i, e.target.value)} />
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

function Paragraph({
  index,
  threadId,
  text,
  segments,
  notes,
  editing,
  readOnly,
  onToggle,
  onChange,
}: {
  index: number;
  threadId: string;
  text: string;
  segments: ReturnType<typeof toSegments>;
  notes: Note[];
  editing: boolean;
  readOnly: boolean;
  onToggle: () => void;
  onChange: (t: string) => void;
}) {
  const [regenOpen, setRegenOpen] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [result, setResult] = useState<{ text: string; removed: string[] } | null>(null);
  const regen = useAction(async () => {
    const r = await endpoints.regenerate(threadId, { paragraph_index: index, instruction: instruction.trim() });
    setResult({ text: r.text, removed: r.removed ?? [] });
  });

  return (
    <article className="para" aria-label={`Paragraph ${index + 1}`} data-testid={`paragraph-${index}`}>
      <div className="para__text">
        {editing ? (
          <>
            <label className="sr-only" htmlFor={`para-${index}`}>
              Edit paragraph {index + 1}
            </label>
            <textarea id={`para-${index}`} className="para__edit" rows={Math.max(4, Math.ceil(text.length / 70))} value={text} onChange={(e) => onChange(e.target.value)} />
          </>
        ) : (
          <p className="para__read">
            {segments.map((s, i) =>
              s.claim ? (
                <EvidenceHover key={i} status={s.claim.status} evidence={s.claim.evidence} note={s.claim.note} testId={`claim-${s.claim.claim_id}`}>
                  {s.text}
                </EvidenceHover>
              ) : (
                <span key={i}>{s.text}</span>
              ),
            )}
          </p>
        )}
        {!readOnly && (
          <div className="para__tools">
            <button type="button" className="btn btn--sm" aria-pressed={editing} onClick={onToggle}>
              {editing ? "Done editing" : "Edit paragraph"}
            </button>
            <button type="button" className="btn btn--sm btn--ghost" aria-expanded={regenOpen} onClick={() => setRegenOpen((o) => !o)}>
              Regenerate paragraph
            </button>
          </div>
        )}
        {regenOpen && !readOnly && (
          <div className="regen">
            <div className="field">
              <label htmlFor={`instr-${index}`}>Instruction (optional)</label>
              <input id={`instr-${index}`} value={instruction} onChange={(e) => setInstruction(e.target.value)} placeholder="For example: shorter, mention the Stripe project" />
            </div>
            <button type="button" className="btn btn--sm" disabled={regen.busy} onClick={() => void regen.call()}>
              {regen.busy ? "Regenerating..." : "Generate new text"}
            </button>
            <InlineError message={regen.error} />
            {result && (
              <div className="regen__result" role="status">
                <p className="prose">{result.text}</p>
                {result.removed.length > 0 && (
                  <p className="muted small">
                    Removed because no evidence supports it: {result.removed.join("; ")}
                  </p>
                )}
                <button
                  type="button"
                  className="btn btn--sm btn--primary"
                  onClick={() => {
                    onChange(result.text);
                    setResult(null);
                    setRegenOpen(false);
                  }}
                >
                  Use this text
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="para__notes">
        {notes.map((n, i) => (
          <p key={i} className={`margin-note margin-note--${n.tone}`}>
            <span className="margin-note__who">{n.tone === "critic" ? "Critic" : "Compliance"}</span>
            {n.kind && <span className="muted small"> {humanize(n.kind)}</span>}
            <span className="margin-note__text">{n.text}</span>
          </p>
        ))}
      </div>
    </article>
  );
}
