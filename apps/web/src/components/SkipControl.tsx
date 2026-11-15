import { useState } from "react";
import { endpoints } from "../lib/endpoints";
import { useAction } from "../lib/hooks";
import { InlineError } from "./States";

/** "Skip" button that asks for a reason (stored as training signal for the scout) before sending. */
export default function SkipControl({ jobId, onSkipped, size = "sm" }: { jobId: string; onSkipped: () => void; size?: "sm" | "md" }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const skip = useAction(async () => {
    await endpoints.skip(jobId, reason.trim() || undefined);
    setOpen(false);
    setReason("");
    onSkipped();
  });

  if (!open) {
    return (
      <button type="button" className={`btn btn--${size === "sm" ? "sm" : "md"}`} onClick={() => setOpen(true)}>
        Skip
      </button>
    );
  }
  return (
    <form
      className="inline-form"
      onSubmit={(e) => {
        e.preventDefault();
        void skip.call();
      }}
    >
      <label className="sr-only" htmlFor={`skip-${jobId}`}>
        Reason for skipping
      </label>
      <input id={`skip-${jobId}`} autoFocus placeholder="Reason (for example: budget too low)" value={reason} onChange={(e) => setReason(e.target.value)} onKeyDown={(e) => e.key === "Escape" && setOpen(false)} />
      <button type="submit" className="btn btn--sm btn--danger" disabled={skip.busy}>
        Confirm skip
      </button>
      <button type="button" className="btn btn--sm btn--ghost" onClick={() => setOpen(false)}>
        Cancel
      </button>
      <InlineError message={skip.error} />
    </form>
  );
}
