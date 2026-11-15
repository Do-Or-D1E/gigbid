import type { Claim } from "./types";

export interface ClaimSpan {
  start: number;
  end: number;
  claim: Claim;
}
export interface Segment {
  text: string;
  claim?: Claim;
}

/** Longest common substring of a and b. Returns its length and where it ends in a. */
export function longestCommonSubstring(a: string, b: string): { len: number; endA: number } {
  let best = 0;
  let endA = 0;
  let prev = new Uint16Array(b.length + 1);
  let cur = new Uint16Array(b.length + 1);
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      if (a.charCodeAt(i - 1) === b.charCodeAt(j - 1)) {
        const v = prev[j - 1] + 1;
        cur[j] = v;
        if (v > best) {
          best = v;
          endA = i;
        }
      } else cur[j] = 0;
    }
    [prev, cur] = [cur, prev];
  }
  return { len: best, endA };
}

const norm = (s: string) => s.toLowerCase();

interface Candidate {
  paragraph: number;
  start: number;
  end: number;
  score: number;
}

function findInParagraph(para: string, claimText: string): Candidate | null {
  const p = norm(para);
  const c = norm(claimText).trim();
  if (!c) return null;
  const exact = p.indexOf(c);
  if (exact >= 0) return { paragraph: 0, start: exact, end: exact + c.length, score: 1_000_000 + c.length };
  const head = c.slice(0, 40);
  if (head.length >= 12) {
    const i = p.indexOf(head);
    if (i >= 0) return { paragraph: 0, start: i, end: Math.min(p.length, i + c.length), score: 100_000 + head.length };
  }
  const { len, endA } = longestCommonSubstring(p, c);
  const threshold = Math.max(12, Math.min(30, Math.floor(c.length / 2)));
  if (len >= threshold) return { paragraph: 0, start: endA - len, end: endA, score: len };
  return null;
}

/**
 * Match claims to the current text of each paragraph (case-insensitive).
 * Order of attempts: exact text, first ~40 characters, longest common substring.
 */
export function matchClaims(paragraphs: string[], claims: Claim[]): { spans: ClaimSpan[][]; unmatched: Claim[] } {
  const spans: ClaimSpan[][] = paragraphs.map(() => []);
  const unmatched: Claim[] = [];
  for (const claim of claims) {
    let best: Candidate | null = null;
    paragraphs.forEach((para, idx) => {
      const c = findInParagraph(para, claim.text);
      if (c && (!best || c.score > best.score)) best = { ...c, paragraph: idx };
    });
    if (!best) {
      unmatched.push(claim);
      continue;
    }
    const b: Candidate = best;
    const list = spans[b.paragraph];
    if (list.some((s) => b.start < s.end && b.end > s.start)) {
      unmatched.push(claim); // overlaps a claim that is already highlighted
      continue;
    }
    list.push({ start: b.start, end: b.end, claim });
  }
  spans.forEach((l) => l.sort((x, y) => x.start - y.start));
  return { spans, unmatched };
}

export function toSegments(text: string, spans: ClaimSpan[]): Segment[] {
  const out: Segment[] = [];
  let pos = 0;
  for (const s of spans) {
    if (s.start > pos) out.push({ text: text.slice(pos, s.start) });
    out.push({ text: text.slice(s.start, s.end), claim: s.claim });
    pos = s.end;
  }
  if (pos < text.length) out.push({ text: text.slice(pos) });
  return out;
}

export function splitParagraphs(letter: string): string[] {
  const parts = letter.split(/\n\s*\n/).map((p) => p.replace(/\s+$/g, ""));
  return parts.length ? parts : [""];
}
export function joinParagraphs(paras: string[]): string {
  return paras.join("\n\n");
}
