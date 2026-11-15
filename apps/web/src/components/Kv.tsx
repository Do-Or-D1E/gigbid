import type { ReactNode } from "react";
import { humanize } from "../lib/format";

function renderValue(v: unknown): ReactNode {
  if (v === null || v === undefined || v === "") return <span className="muted">-</span>;
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "number" || typeof v === "string") return String(v);
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="muted">None</span>;
    if (v.every((x) => typeof x === "string" || typeof x === "number"))
      return (
        <ul className="plain-list">
          {v.map((x, i) => (
            <li key={i}>{String(x)}</li>
          ))}
        </ul>
      );
    return (
      <ul className="plain-list">
        {v.map((x, i) => (
          <li key={i}>{typeof x === "object" ? compact(x) : String(x)}</li>
        ))}
      </ul>
    );
  }
  return compact(v);
}

function compact(o: unknown): string {
  try {
    return JSON.stringify(o);
  } catch {
    return String(o);
  }
}

/** Generic key/value list for backend objects whose exact fields are not fixed by the OpenAPI schema. */
export default function Kv({ data, skip = [] }: { data: Record<string, unknown> | null | undefined; skip?: string[] }) {
  const entries = Object.entries(data ?? {}).filter(([k]) => !skip.includes(k));
  if (entries.length === 0) return <p className="muted">Nothing to show.</p>;
  return (
    <dl className="kv kv--list">
      {entries.map(([k, v]) => (
        <div key={k}>
          <dt>{humanize(k)}</dt>
          <dd>{renderValue(v)}</dd>
        </div>
      ))}
    </dl>
  );
}
