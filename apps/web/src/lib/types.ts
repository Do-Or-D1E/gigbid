import type { components } from "./api/schema";

type S = components["schemas"];
export type UserOut = S["UserOut"];
export type JobCard = S["JobCard"];
export type ApprovalOut = S["ApprovalOut"];
export type RunRef = S["RunRef"];
export type RunOut = S["RunOut"];
export type RunDetailOut = S["RunDetailOut"];
export type RunEventOut = S["RunEventOut"];
export type SettingsOut = S["SettingsOut"];
export type PortfolioItemOut = S["PortfolioItemOut"];

/** Shapes inside ApprovalOut.payload (the OpenAPI schema types it as a free-form object). */
export type ClaimStatus = "supported" | "partly_supported" | "unsupported";

export interface EvidenceLite {
  item_id: string;
  title: string;
  snippet: string;
  source?: string;
}
export interface Claim {
  claim_id: string;
  text: string;
  status: ClaimStatus;
  note?: string;
  evidence_ids?: string[];
  evidence?: EvidenceLite[];
}
export interface CritiqueIssue {
  kind: string;
  detail: string;
  paragraph?: number | null;
}
export interface Critique {
  verdict: string;
  score?: number;
  issues?: CritiqueIssue[];
  round?: number;
}
export interface Violation {
  rule_id: string;
  excerpt?: string;
  action?: string;
}
export interface Compliance {
  verdict: string;
  violations?: Violation[];
  reason?: string;
}
export interface Preview {
  payload?: unknown;
  policy_warnings?: string[];
  connects_cost?: number;
  connects_balance?: number;
  balance_after?: number;
}
export interface ProposalPayload {
  job?: {
    job_id: string;
    title: string;
    category?: string;
    budget_type?: string;
    budget_min?: number;
    budget_max?: number;
    client_id?: string;
  };
  draft?: {
    cover_letter: string;
    screening_answers?: { question: string; answer: string }[];
    cited_evidence_ids?: string[];
    version?: number;
  };
  claims?: Claim[];
  claim_report?: {
    unsupported_before?: number;
    unsupported_after?: number;
    rewritten?: number;
    unsupported_before_first_draft?: number;
  };
  risk?: {
    risk_score?: number;
    client_quality?: string | number;
    is_scam?: boolean;
    flags?: { kind: string; evidence: string; severity: string }[];
    injected_instructions?: string[];
    summary?: string;
  };
  fit?: {
    fit_score?: number;
    coverage?: number;
    matches?: { requirement: string; strength: string; evidence_ids?: string[]; reason?: string }[];
    missing?: string[];
    reasons?: string[];
  };
  price?: Record<string, number | string | boolean | null | undefined>;
  critiques?: Critique[];
  compliance?: Compliance;
  preview?: Preview;
  decision?: { action?: string; reasons?: string[] };
}
export interface MessagePayload {
  thread_id?: string;
  job_id?: string;
  intent?: { intent: string; confidence?: number; summary?: string };
  reply?: { text: string; proposed_slots?: string[]; create_hold?: boolean };
  slots?: { start: string; end: string; label?: string }[];
  client_message?: { sender: string; text: string };
  compliance?: Compliance;
  injection_hits?: string[];
  preview?: Preview;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AnyRec = Record<string, any>;
