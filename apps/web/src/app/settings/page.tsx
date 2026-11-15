import { useEffect, useState } from "react";
import { endpoints } from "../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../lib/hooks";
import { dateTime, humanize } from "../../lib/format";
import { EmptyState, ErrorState, InlineError, PageHeader, Skeleton } from "../../components/States";
import { useToast } from "../../lib/toast";
import type { SettingsOut } from "../../lib/types";

type Autonomy = "suggest" | "auto_skip_low_fit";
type Kind = "case_study" | "repo" | "review" | "upload";

export default function SettingsPage() {
  useDocumentTitle("Settings");
  const settings = useAsync(() => endpoints.settings(), []);
  const s = settings.data;

  return (
    <>
      <PageHeader title="Settings" sub="How GigBid works for you." />
      {settings.loading && <Skeleton lines={8} height={22} />}
      {settings.error && <ErrorState message={settings.error} onRetry={settings.reload} />}
      {s && (
        <>
          <Preferences key={`${s.autonomy}${s.hourly_rate_usd}${s.min_project_usd}${s.weekly_connects_budget}`} initial={s} onSaved={(n) => settings.setData(n)} />
          <Searches searches={s.saved_searches ?? []} onChanged={() => void settings.reload()} />
          <Accounts accounts={s.connected_accounts ?? []} />
          <Portfolio onChanged={() => void settings.reload()} />
          <Memory />
          <section className="card" aria-labelledby="h-sys">
            <h2 id="h-sys" className="h3">
              System
            </h2>
            <p className="muted small">Set by your administrator. Read only.</p>
            <dl className="kv kv--tight" data-testid="system-info">
              <div>
                <dt>Model profile</dt>
                <dd>{s.model_profile ?? "-"}</dd>
              </div>
              <div>
                <dt>Marketplace mode</dt>
                <dd>{s.marketplace_mode ?? "-"}</dd>
              </div>
              <div>
                <dt>Policy version</dt>
                <dd>{s.policy_version ?? "-"}</dd>
              </div>
              <div>
                <dt>RAG variant</dt>
                <dd>{s.rag_variant ?? "-"}</dd>
              </div>
            </dl>
          </section>
        </>
      )}
    </>
  );
}

function Preferences({ initial, onSaved }: { initial: SettingsOut; onSaved: (s: SettingsOut) => void }) {
  const toast = useToast();
  const [autonomy, setAutonomy] = useState<Autonomy>(initial.autonomy ?? "suggest");
  const [hourly, setHourly] = useState(String(initial.hourly_rate_usd ?? ""));
  const [minp, setMinp] = useState(String(initial.min_project_usd ?? ""));
  const [connects, setConnects] = useState(String(initial.weekly_connects_budget ?? ""));
  const save = useAction(async () => {
    const out = await endpoints.saveSettings({
      autonomy,
      hourly_rate_usd: hourly === "" ? null : Number(hourly),
      min_project_usd: minp === "" ? null : Number(minp),
      weekly_connects_budget: connects === "" ? null : Math.round(Number(connects)),
    });
    onSaved(out);
    toast.ok("Settings saved.");
  });

  return (
    <form
      className="card"
      aria-labelledby="h-pref"
      onSubmit={(e) => {
        e.preventDefault();
        void save.call();
      }}
    >
      <h2 id="h-pref" className="h3">
        Autonomy, rates and budget
      </h2>
      <fieldset className="choice-grid choice-grid--tight">
        <legend>Autonomy level</legend>
        <label className={`choice${autonomy === "suggest" ? " is-selected" : ""}`}>
          <input type="radio" name="autonomy" checked={autonomy === "suggest"} onChange={() => setAutonomy("suggest")} />
          <span className="choice__title">Suggest only</span>
          <span className="choice__sub">GigBid scores jobs and drafts proposals. You decide on everything.</span>
        </label>
        <label className={`choice${autonomy === "auto_skip_low_fit" ? " is-selected" : ""}`}>
          <input type="radio" name="autonomy" checked={autonomy === "auto_skip_low_fit"} onChange={() => setAutonomy("auto_skip_low_fit")} />
          <span className="choice__title">Skip low-fit jobs automatically</span>
          <span className="choice__sub">GigBid hides jobs that clearly do not fit. You can still find them under the Skipped filter.</span>
        </label>
      </fieldset>
      <p className="note">GigBid never sends a proposal or message on its own, at any autonomy level. Every send needs your approval.</p>
      <div className="form form--grid">
        <div className="field">
          <label htmlFor="s-rate">Hourly rate (USD)</label>
          <input id="s-rate" type="number" min={0} value={hourly} onChange={(e) => setHourly(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="s-min">Minimum project (USD)</label>
          <input id="s-min" type="number" min={0} value={minp} onChange={(e) => setMinp(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="s-cb">Weekly Connects budget</label>
          <input id="s-cb" type="number" min={0} value={connects} onChange={(e) => setConnects(e.target.value)} />
        </div>
      </div>
      <InlineError message={save.error} />
      <button type="submit" className="btn btn--primary" disabled={save.busy}>
        {save.busy ? "Saving..." : "Save settings"}
      </button>
    </form>
  );
}

function Searches({ searches, onChanged }: { searches: NonNullable<SettingsOut["saved_searches"]>; onChanged: () => void }) {
  const toast = useToast();
  const [form, setForm] = useState({ name: "", query: "", category: "", interval: "60" });
  const add = useAction(async () => {
    await endpoints.addSearch({ name: form.name.trim(), query: form.query.trim(), category: form.category.trim() || null, interval_minutes: Number(form.interval) || 60 });
    setForm({ name: "", query: "", category: "", interval: "60" });
    toast.ok("Search saved.");
    onChanged();
  });
  const del = useAction(async (id: number) => {
    await endpoints.deleteSearch(id);
    toast.ok("Search deleted.");
    onChanged();
  });
  return (
    <section className="card" aria-labelledby="h-search">
      <h2 id="h-search" className="h3">
        Saved searches
      </h2>
      {searches.length === 0 ? (
        <p className="muted">No saved searches. GigBid needs at least one to scout for jobs.</p>
      ) : (
        <ul className="rows">
          {searches.map((x) => (
            <li key={x.id} className="rows__item">
              <div>
                <strong>{x.name}</strong>
                <p className="muted small">
                  {[x.query && `"${x.query}"`, x.category, `every ${x.interval_minutes ?? 60} min`, x.last_run_at && `last run ${dateTime(x.last_run_at)}`].filter(Boolean).join(" | ")}
                </p>
              </div>
              <button type="button" className="btn btn--sm btn--danger" aria-label={`Delete search ${x.name}`} disabled={del.busy} onClick={() => void del.call(x.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      <InlineError message={del.error} />
      <form
        className="form form--grid"
        aria-label="Add a saved search"
        onSubmit={(e) => {
          e.preventDefault();
          void add.call();
        }}
      >
        <div className="field">
          <label htmlFor="ns-name">Name</label>
          <input id="ns-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="ns-q">Keywords</label>
          <input id="ns-q" value={form.query} onChange={(e) => setForm({ ...form, query: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="ns-c">Category (optional)</label>
          <input id="ns-c" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="ns-i">Check every (minutes)</label>
          <input id="ns-i" type="number" min={5} value={form.interval} onChange={(e) => setForm({ ...form, interval: e.target.value })} />
        </div>
        <div>
          <button type="submit" className="btn" disabled={add.busy || !form.name.trim()}>
            Add search
          </button>
        </div>
      </form>
      <InlineError message={add.error} />
    </section>
  );
}

function Accounts({ accounts }: { accounts: NonNullable<SettingsOut["connected_accounts"]> }) {
  const connect = useAction(async () => {
    const r = await endpoints.upworkStart();
    const url = (r.authorize_url ?? r.url) as string | undefined;
    if (!url) throw new Error("The server did not return an Upwork authorize URL.");
    window.location.assign(url);
  });
  return (
    <section className="card" aria-labelledby="h-acc">
      <h2 id="h-acc" className="h3">
        Connected accounts
      </h2>
      {accounts.length === 0 ? (
        <p className="muted">No marketplace is connected.</p>
      ) : (
        <ul className="rows">
          {accounts.map((a) => (
            <li key={`${a.mode}-${a.account_id}`} className="rows__item">
              <div>
                <strong>{a.mode === "gigsim" ? "GigSim" : a.mode === "upwork_live" ? "Upwork" : a.mode}</strong>
                <p className="muted small">
                  {a.account_id}
                  {a.connected_at ? ` | connected ${dateTime(a.connected_at)}` : ""}
                </p>
              </div>
              <span className="pill pill--done">Connected</span>
            </li>
          ))}
        </ul>
      )}
      <InlineError message={connect.error} />
      <button type="button" className="btn" disabled={connect.busy} onClick={() => void connect.call()}>
        Connect Upwork
      </button>
    </section>
  );
}

function Portfolio({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const items = useAsync(() => endpoints.portfolio(), []);
  const [up, setUp] = useState<{ title: string; text: string; kind: Kind }>({ title: "", text: "", kind: "case_study" });
  const toggle = useAction(async (id: string, hidden: boolean) => {
    if (hidden) await endpoints.unhideItem(id);
    else await endpoints.hideItem(id);
    await items.reload();
    onChanged();
  });
  const upload = useAction(async () => {
    await endpoints.upload({ title: up.title.trim(), text: up.text.trim(), kind: up.kind });
    setUp({ title: "", text: "", kind: "case_study" });
    toast.ok("Portfolio item added.");
    await items.reload();
  });
  return (
    <section className="card" aria-labelledby="h-port">
      <h2 id="h-port" className="h3">
        Portfolio
      </h2>
      <p className="muted small">GigBid only cites visible items as evidence. Hidden items are never used.</p>
      {items.loading && <Skeleton lines={3} />}
      {items.error && <ErrorState title="Could not load portfolio" message={items.error} onRetry={items.reload} />}
      {items.data && items.data.length === 0 && <EmptyState title="No portfolio items">Add case studies, repositories or client reviews so proposals can cite them.</EmptyState>}
      <ul className="rows">
        {(items.data ?? []).map((it) => (
          <li key={it.item_id} className={`rows__item${it.hidden ? " is-muted" : ""}`}>
            <div>
              <strong>{it.title}</strong>
              <p className="muted small">
                {humanize(it.type)}
                {it.date ? ` | ${it.date}` : ""}
                {it.hidden ? " | hidden" : ""}
              </p>
            </div>
            <button type="button" className="btn btn--sm" aria-label={`${it.hidden ? "Unhide" : "Hide"} ${it.title}`} disabled={toggle.busy} onClick={() => void toggle.call(it.item_id, !!it.hidden)}>
              {it.hidden ? "Unhide" : "Hide"}
            </button>
          </li>
        ))}
      </ul>
      <InlineError message={toggle.error} />
      <details className="details">
        <summary>Add an item</summary>
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            void upload.call();
          }}
        >
          <div className="field">
            <label htmlFor="pu-title">Title</label>
            <input id="pu-title" required value={up.title} onChange={(e) => setUp({ ...up, title: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="pu-kind">Type</label>
            <select id="pu-kind" value={up.kind} onChange={(e) => setUp({ ...up, kind: e.target.value as Kind })}>
              <option value="case_study">Case study</option>
              <option value="repo">Repository</option>
              <option value="review">Client review</option>
              <option value="upload">Other</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="pu-text">Text</label>
            <textarea id="pu-text" required rows={5} value={up.text} onChange={(e) => setUp({ ...up, text: e.target.value })} />
          </div>
          <InlineError message={upload.error} />
          <button type="submit" className="btn" disabled={upload.busy || !up.title.trim() || !up.text.trim()}>
            Upload item
          </button>
        </form>
      </details>
    </section>
  );
}

function Memory() {
  const toast = useToast();
  const mem = useAsync(() => endpoints.memory(), []);
  const [confirm, setConfirm] = useState<string | null>(null);
  useEffect(() => {
    if (!confirm) return;
    const t = setTimeout(() => setConfirm(null), 6000);
    return () => clearTimeout(t);
  }, [confirm]);
  const del = useAction(async (kind: string, key: string) => {
    await endpoints.deleteMemory(kind, key);
    setConfirm(null);
    toast.ok("Memory item deleted.");
    await mem.reload();
  });

  const list = (kind: "style" | "outcome", items: NonNullable<typeof mem.data>["style"]) =>
    items.length === 0 ? (
      <p className="muted">Nothing learned yet.</p>
    ) : (
      <ul className="rows">
        {items.map((m) => {
          const id = `${kind}/${m.key}`;
          return (
            <li key={id} className="rows__item">
              <div>
                <p>{m.text}</p>
                <p className="muted small">
                  {m.support != null ? `Seen ${m.support} time${m.support === 1 ? "" : "s"}` : ""}
                  {m.detail && Object.keys(m.detail).length > 0 ? ` | ${Object.entries(m.detail).map(([k, v]) => `${humanize(k)}: ${String(v)}`).join(", ")}` : ""}
                </p>
              </div>
              {confirm === id ? (
                <span className="row">
                  <button type="button" className="btn btn--sm btn--danger" disabled={del.busy} onClick={() => void del.call(kind, m.key)}>
                    Confirm delete
                  </button>
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => setConfirm(null)}>
                    Cancel
                  </button>
                </span>
              ) : (
                <button type="button" className="btn btn--sm" aria-label={`Delete memory: ${m.text}`} onClick={() => setConfirm(id)}>
                  Delete
                </button>
              )}
            </li>
          );
        })}
      </ul>
    );

  return (
    <section className="card" aria-labelledby="h-mem">
      <h2 id="h-mem" className="h3">
        What GigBid has learned
      </h2>
      {mem.loading && <Skeleton lines={4} />}
      {mem.error && <ErrorState title="Could not load memory" message={mem.error} onRetry={mem.reload} />}
      {mem.data && (
        <>
          <p className="note">{mem.data.promotion_rule}</p>
          <InlineError message={del.error} />
          <h3 className="h4">Style rules</h3>
          {list("style", mem.data.style)}
          <h3 className="h4">Outcome insights</h3>
          {list("outcome", mem.data.outcome)}
          <h3 className="h4">Edits waiting to become rules</h3>
          {(mem.data.pending_edits ?? []).length === 0 ? (
            <p className="muted">No pending edit patterns.</p>
          ) : (
            <ul className="plain-list">
              {mem.data.pending_edits!.map((features, i) => (
                <li key={i}>{features.join(", ")}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
