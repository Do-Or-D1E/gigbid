import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { ClaimStatus, EvidenceLite } from "../lib/types";

export const STATUS_LABEL: Record<ClaimStatus, string> = {
  supported: "Supported",
  partly_supported: "Partly supported",
  unsupported: "Unsupported",
};

interface Props {
  children: ReactNode;
  evidence?: EvidenceLite[];
  status?: ClaimStatus;
  note?: string;
  /** Show the trigger as plain inline text instead of a highlighted claim (used in tables). */
  variant?: "claim" | "link";
  testId?: string;
}

/**
 * Shows the evidence behind a claim in a popover.
 * Opens on hover and on keyboard focus, closes on blur, mouse leave and Escape.
 * Everything inside the popover is a span so it is valid inside paragraphs.
 */
export default function EvidenceHover({ children, evidence = [], status, note, variant = "claim", testId }: Props) {
  const [open, setOpen] = useState(false);
  const hovering = useRef(false);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const cls = variant === "claim" ? `claim claim--${status ?? "supported"}` : "evlink";
  return (
    <span
      className="evh"
      onMouseEnter={() => {
        hovering.current = true;
        setOpen(true);
      }}
      onMouseLeave={() => {
        hovering.current = false;
        setOpen(false);
      }}
    >
      <span
        role="button"
        tabIndex={0}
        className={cls}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        data-testid={testId}
        onFocus={() => setOpen(true)}
        onBlur={() => !hovering.current && setOpen(false)}
        onClick={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen(true);
          }
        }}
      >
        {children}
        {status && status !== "supported" && <span className="sr-only"> ({STATUS_LABEL[status]})</span>}
      </span>
      {open && (
        <span role="tooltip" id={id} className="evh__pop">
          {status && <span className={`evh__status evh__status--${status}`}>{STATUS_LABEL[status]}</span>}
          {note && <span className="evh__note">{note}</span>}
          {evidence.length === 0 ? (
            <span className="evh__none">No evidence found for this claim.</span>
          ) : (
            evidence.map((e) => (
              <span key={e.item_id} className="evh__item">
                <span className="evh__title">{e.title}</span>
                <span className="evh__snippet">{e.snippet}</span>
                {e.source && <span className="evh__source">Source: {e.source}</span>}
              </span>
            ))
          )}
        </span>
      )}
    </span>
  );
}
