export function money(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  const d = n !== 0 && Math.abs(n) < 1 ? Math.max(digits, 3) : digits;
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: d, maximumFractionDigits: d });
}
export function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return n.toLocaleString("en-US", { maximumFractionDigits: digits });
}
export function pct(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  const v = n <= 1 ? n * 100 : n;
  return `${v.toFixed(digits)}%`;
}
export function budgetText(j: { budget_type?: string | null; budget_min?: number | null; budget_max?: number | null }): string {
  const { budget_type: t, budget_min: lo, budget_max: hi } = j;
  const unit = t === "hourly" ? "/hr" : "";
  if (lo != null && hi != null && lo !== hi) return `${money(lo)} to ${money(hi)}${unit}`;
  const v = hi ?? lo;
  return v != null ? `${money(v)}${unit}` : "No budget";
}
export function dateTime(s: string | null | undefined): string {
  if (!s) return "-";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
export function timeAgo(s: string | null | undefined): string {
  if (!s) return "";
  const d = new Date(s).getTime();
  if (Number.isNaN(d)) return s;
  const sec = Math.max(0, (Date.now() - d) / 1000);
  if (sec < 60) return "just now";
  if (sec < 3600) return `${Math.floor(sec / 60)} min ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} h ago`;
  return `${Math.floor(sec / 86400)} d ago`;
}
export function humanize(key: string): string {
  const s = key.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
export function seconds(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return n < 10 ? `${n.toFixed(2)} s` : `${n.toFixed(1)} s`;
}
export function asList(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => (typeof x === "string" ? x : JSON.stringify(x)));
  if (v == null || v === "") return [];
  return [String(v)];
}
