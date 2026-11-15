import { endpoints } from "../../lib/endpoints";
import { useAsync, useDocumentTitle } from "../../lib/hooks";
import { humanize, money, num, pct, seconds } from "../../lib/format";
import { EmptyState, ErrorState, PageHeader, Skeleton } from "../../components/States";

function Bar({ value, max, tone, label }: { value: number; max: number; tone: string; label: string }) {
  const w = max > 0 ? Math.max(value > 0 ? 2 : 0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <svg className={`bar bar--${tone}`} viewBox="0 0 100 8" preserveAspectRatio="none" role="img" aria-label={label}>
      <rect className="bar__track" x="0" y="0" width="100" height="8" rx="2" />
      <rect className="bar__fill" x="0" y="0" width={w} height="8" rx="2" />
    </svg>
  );
}

const WORDS = ["budget", "declared", "target", "max", "limit"];
const norm = (k: string) =>
  k
    .split("_")
    .filter((t) => !WORDS.includes(t))
    .join("_");

/** Show measured values next to the declared budget with the same base name, when the API provides one. */
function BudgetTable({ data, fmt, empty }: { data: Record<string, number | null>; fmt: (n: number | null | undefined) => string; empty: string }) {
  const keys = Object.keys(data);
  if (keys.length === 0) return <p className="muted">{empty}</p>;
  const isBudget = (k: string) => WORDS.some((w) => k.split("_").includes(w));
  const budgets = new Map<string, string>();
  keys.filter(isBudget).forEach((k) => budgets.set(norm(k), k));
  const rows = keys.filter((k) => !isBudget(k));
  const orphan = keys.filter((k) => isBudget(k) && !rows.some((r) => norm(r) === norm(k)));
  const line = (k: string, budgetKey?: string) => {
    const v = data[k];
    const b = budgetKey ? data[budgetKey] : undefined;
    const over = v != null && b != null && v > b;
    return (
      <tr key={k}>
        <th scope="row">{humanize(k)}</th>
        <td className="num">{fmt(v)}</td>
        <td className="num">{budgetKey ? fmt(b) : <span className="muted">-</span>}</td>
        <td>
          {budgetKey && v != null && b != null && b > 0 ? (
            <span className="meter">
              <Bar value={v} max={Math.max(v, b)} tone={over ? "bad" : "ok"} label={`${humanize(k)} is ${Math.round((v / b) * 100)} percent of the declared budget`} />
              <span className={over ? "text-bad small" : "muted small"}>{over ? "Over budget" : "Within budget"}</span>
            </span>
          ) : null}
        </td>
      </tr>
    );
  };
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Measure</th>
            <th scope="col" className="num">Actual</th>
            <th scope="col" className="num">Declared budget</th>
            <th scope="col">Compared</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((k) => line(k, budgets.get(norm(k))))}
          {orphan.map((k) => line(k))}
        </tbody>
      </table>
    </div>
  );
}

export default function AnalyticsPage() {
  useDocumentTitle("Analytics");
  const a = useAsync(() => endpoints.analytics(), []);
  if (a.loading) return <Skeleton lines={8} height={22} />;
  if (a.error || !a.data) return <ErrorState message={a.error ?? "No data."} onRetry={a.reload} />;
  const d = a.data;

  const sub = d.by_category.reduce((n, c) => n + c.submitted, 0);
  const rep = d.by_category.reduce((n, c) => n + c.replied, 0);
  const hired = d.by_category.reduce((n, c) => n + c.hired, 0);
  const maxRate = Math.max(0.0001, ...d.by_category.flatMap((c) => [c.reply_rate, c.hire_rate]));
  const asRate = (r: number) => (r <= 1 ? r : r / 100);

  const reasons = d.rejection_reasons.map((r) => {
    const label = Object.values(r).find((v) => typeof v === "string") as string | undefined;
    const count = Object.values(r).find((v) => typeof v === "number") as number | undefined;
    return { label: label ?? "Unspecified", count: count ?? 1 };
  });
  const maxReason = Math.max(1, ...reasons.map((r) => r.count));
  const decisions = Object.entries(d.decisions);
  const maxDecision = Math.max(1, ...decisions.map(([, n]) => n));
  const empty = d.proposals === 0 && d.jobs_analysed === 0 && sub === 0;

  return (
    <>
      <PageHeader title="Analytics" sub="What your proposals earn, what they cost, and what you reject." />
      {empty && <EmptyState title="No data yet">Analyse jobs and send proposals. Reply rates, costs and rejection reasons appear here.</EmptyState>}

      <section className="tiles" aria-label="Totals">
        <div className="tile">
          <span className="tile__v">{num(d.jobs_analysed)}</span>
          <span className="tile__l">Jobs analysed</span>
        </div>
        <div className="tile">
          <span className="tile__v">{num(d.proposals)}</span>
          <span className="tile__l">Proposals</span>
        </div>
        <div className="tile">
          <span className="tile__v">{num(d.connects_spent)}</span>
          <span className="tile__l">Connects spent</span>
        </div>
        <div className="tile">
          <span className="tile__v">{d.connects_per_reply != null ? num(d.connects_per_reply, 1) : "-"}</span>
          <span className="tile__l">Connects per reply</span>
        </div>
      </section>

      <section className="card" aria-labelledby="h-cat">
        <h2 id="h-cat" className="h3">
          Reply and hire rate by category
        </h2>
        {d.by_category.length === 0 ? (
          <p className="muted">No submitted proposals yet.</p>
        ) : (
          <>
            <ul className="legend">
              <li>
                <span className="swatch swatch--reply" aria-hidden="true" /> Reply rate
              </li>
              <li>
                <span className="swatch swatch--hire" aria-hidden="true" /> Hire rate
              </li>
            </ul>
            <ul className="bars" data-testid="category-chart">
              {d.by_category.map((c) => (
                <li key={c.category} className="bars__row">
                  <span className="bars__label">
                    {c.category} <span className="muted small">{c.submitted} sent</span>
                  </span>
                  <span className="bars__pair">
                    <span className="bars__line">
                      <Bar value={asRate(c.reply_rate)} max={asRate(maxRate)} tone="reply" label={`${c.category} reply rate ${pct(c.reply_rate)}`} />
                      <span className="bars__val">{pct(c.reply_rate)}</span>
                    </span>
                    <span className="bars__line">
                      <Bar value={asRate(c.hire_rate)} max={asRate(maxRate)} tone="hire" label={`${c.category} hire rate ${pct(c.hire_rate)}`} />
                      <span className="bars__val">{pct(c.hire_rate)}</span>
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="card" aria-labelledby="h-conn">
        <h2 id="h-conn" className="h3">
          Connects spent and outcomes
        </h2>
        <ul className="bars">
          {[
            { l: "Proposals sent", v: sub, tone: "sent" },
            { l: "Replies", v: rep, tone: "reply" },
            { l: "Hired", v: hired, tone: "hire" },
          ].map((r) => (
            <li key={r.l} className="bars__row bars__row--single">
              <span className="bars__label">{r.l}</span>
              <span className="bars__line">
                <Bar value={r.v} max={sub} tone={r.tone} label={`${r.l}: ${r.v}`} />
                <span className="bars__val">{num(r.v)}</span>
              </span>
            </li>
          ))}
        </ul>
        <dl className="kv kv--tight">
          <div>
            <dt>Connects spent</dt>
            <dd>{num(d.connects_spent)}</dd>
          </div>
          <div>
            <dt>Per reply</dt>
            <dd>{d.connects_per_reply != null ? num(d.connects_per_reply, 1) : "-"}</dd>
          </div>
          <div>
            <dt>Per hire</dt>
            <dd>{hired > 0 ? num(d.connects_spent / hired, 1) : "-"}</dd>
          </div>
        </dl>
      </section>

      <div className="grid grid--2">
        <section className="card" aria-labelledby="h-cost">
          <h2 id="h-cost" className="h3">
            Cost per job and per proposal
          </h2>
          <BudgetTable data={d.cost} fmt={(n) => money(n, 4)} empty="No cost data yet." />
        </section>
        <section className="card" aria-labelledby="h-lat">
          <h2 id="h-lat" className="h3">
            Latency per job and per proposal
          </h2>
          <BudgetTable data={d.latency} fmt={(n) => seconds(n)} empty="No latency data yet." />
        </section>
      </div>

      <div className="grid grid--2">
        <section className="card" aria-labelledby="h-rej">
          <h2 id="h-rej" className="h3">
            Top rejection reasons
          </h2>
          {reasons.length === 0 ? (
            <p className="muted">You have not rejected anything yet.</p>
          ) : (
            <ul className="bars">
              {reasons.map((r, i) => (
                <li key={i} className="bars__row bars__row--single">
                  <span className="bars__label">{r.label}</span>
                  <span className="bars__line">
                    <Bar value={r.count} max={maxReason} tone="bad" label={`${r.label}: ${r.count}`} />
                    <span className="bars__val">{r.count}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="card" aria-labelledby="h-dec">
          <h2 id="h-dec" className="h3">
            Decisions
          </h2>
          {decisions.length === 0 ? (
            <p className="muted">No decisions recorded yet.</p>
          ) : (
            <ul className="bars">
              {decisions.map(([k, n]) => (
                <li key={k} className="bars__row bars__row--single">
                  <span className="bars__label">{humanize(k)}</span>
                  <span className="bars__line">
                    <Bar value={n} max={maxDecision} tone="sent" label={`${humanize(k)}: ${n}`} />
                    <span className="bars__val">{n}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}
