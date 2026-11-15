interface Flag {
  kind: string;
  evidence?: string;
  severity?: string;
}

export function riskLevel(score: number | null | undefined): "low" | "medium" | "high" | "unknown" {
  if (score == null) return "unknown";
  const s = score <= 1 ? score * 100 : score;
  if (s >= 60) return "high";
  if (s >= 30) return "medium";
  return "low";
}

const LABEL = { low: "Low risk", medium: "Medium risk", high: "High risk", unknown: "Risk not scored" } as const;

export default function RiskBadge({
  score,
  flags = [],
  injection,
  scam,
}: {
  score?: number | null;
  flags?: Flag[] | null;
  injection?: boolean;
  scam?: boolean;
}) {
  const level = scam ? "high" : riskLevel(score);
  const shown = score == null ? "" : ` ${score <= 1 ? Math.round(score * 100) : Math.round(score)}`;
  const flagText = (flags ?? []).map((f) => f.kind.replace(/_/g, " ")).join(", ");
  return (
    <span className="badge-row">
      <span
        className={`badge badge--risk-${level}`}
        title={flagText || undefined}
        aria-label={`${LABEL[level]}${shown ? ` score${shown}` : ""}${flagText ? `. Flags: ${flagText}` : ""}`}
      >
        {scam ? "Likely scam" : LABEL[level]}
        {shown}
      </span>
      {(flags ?? []).slice(0, 2).map((f, i) => (
        <span key={i} className={`badge badge--flag badge--sev-${f.severity ?? "low"}`}>
          {f.kind.replace(/_/g, " ")}
        </span>
      ))}
      {(flags ?? []).length > 2 && <span className="badge badge--flag">+{(flags ?? []).length - 2}</span>}
      {injection && (
        <span className="badge badge--risk-high" title="The job text contains instructions aimed at the AI. GigBid ignores them.">
          Prompt injection found
        </span>
      )}
    </span>
  );
}

export function ActionChip({ action }: { action?: string | null }) {
  if (!action) return <span className="chip chip--none">Not analysed</span>;
  const label = action === "bid" ? "Bid" : action === "watch" ? "Watch" : action === "skip" ? "Skip" : action;
  return <span className={`chip chip--${action}`}>Recommended: {label}</span>;
}

export function StatusPill({ status }: { status?: string | null }) {
  if (!status) return null;
  return <span className={`pill pill--${status.toLowerCase().replace(/[^a-z]/g, "-")}`}>{status.replace(/_/g, " ")}</span>;
}
