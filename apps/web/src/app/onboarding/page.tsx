import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { endpoints } from "../../lib/endpoints";
import { useAction, useAsync, useDocumentTitle } from "../../lib/hooks";
import { EmptyState, ErrorState, InlineError, Skeleton } from "../../components/States";
import MarketplaceBanner from "../../components/MarketplaceBanner";
import { useToast } from "../../lib/toast";
import { money } from "../../lib/format";

const STEPS = ["Profile", "Marketplace", "Portfolio", "Rates", "First search"];
const OWN = "__own__";
type Kind = "case_study" | "repo" | "review" | "upload";

export default function OnboardingPage() {
  useDocumentTitle("Set up");
  const nav = useNavigate();
  const toast = useToast();
  const { refresh, user } = useAuth();
  const personas = useAsync(() => endpoints.personas(), []);

  const [step, setStep] = useState(0);
  const [choice, setChoice] = useState<string>("");
  const [base, setBase] = useState<string>("");
  const [marketplace, setMarketplace] = useState<"gigsim" | "upwork_live">("gigsim");
  const [uploaded, setUploaded] = useState<string[]>([]);
  const [up, setUp] = useState<{ title: string; text: string; kind: Kind }>({ title: "", text: "", kind: "case_study" });
  const [hourly, setHourly] = useState("");
  const [minProject, setMinProject] = useState("");
  const [connects, setConnects] = useState("");
  const [search, setSearch] = useState({ name: "", query: "", category: "", interval: "60" });

  const list = personas.data ?? [];
  const personaId = choice === OWN ? base : choice;
  const persona = list.find((p) => p.id === personaId);

  // Prefill rates and the first search from the chosen persona.
  useEffect(() => {
    if (!persona) return;
    setHourly(String(persona.hourly_rate_usd));
    setMinProject(String(persona.min_project_usd));
    setConnects(String(persona.weekly_connects_budget));
    setSearch((s) => ({ ...s, name: s.name || "My first search", query: s.query || persona.skills.slice(0, 2).join(" ") }));
  }, [persona]);

  const upload = useAction(async () => {
    const item = await endpoints.upload({ title: up.title.trim(), text: up.text.trim(), kind: up.kind });
    setUploaded((u) => [...u, item.title]);
    setUp({ title: "", text: "", kind: "case_study" });
    toast.ok("Portfolio item added.");
  });

  const connect = useAction(async () => {
    const r = await endpoints.upworkStart();
    const url = (r.authorize_url ?? r.url) as string | undefined;
    if (!url) throw new Error("The server did not return an Upwork authorize URL.");
    window.location.assign(url);
  });

  const finish = useAction(async () => {
    await endpoints.onboard({
      persona_id: personaId,
      marketplace,
      hourly_rate_usd: Number(hourly),
      min_project_usd: Number(minProject),
      weekly_connects_budget: Math.round(Number(connects)),
      saved_search: search.name.trim() ? { name: search.name.trim(), query: search.query.trim(), category: search.category.trim() || null, interval_minutes: Number(search.interval) || 60 } : null,
    });
    await refresh();
    toast.ok("Setup complete.");
    nav("/inbox", { replace: true });
  });

  const canNext = [
    !!personaId,
    true,
    choice !== OWN || uploaded.length > 0,
    Number(hourly) > 0 && Number(minProject) >= 0 && hourly !== "" && minProject !== "" && Number(connects) >= 0 && connects !== "",
    true,
  ][step];

  return (
    <div className="auth auth--wide">
      <MarketplaceBanner />
      <div className="wizard card">
        <h1>Set up GigBid{user?.name ? `, ${user.name.split(" ")[0]}` : ""}</h1>
        <ol className="steps" aria-label="Setup steps">
          {STEPS.map((s, i) => (
            <li key={s} className={i === step ? "is-current" : i < step ? "is-done" : ""} aria-current={i === step ? "step" : undefined}>
              <span className="steps__n">{i + 1}</span> {s}
            </li>
          ))}
        </ol>

        {step === 0 && (
          <section aria-labelledby="s0">
            <h2 id="s0" className="h3">
              Who are you bidding as?
            </h2>
            {personas.loading && <Skeleton lines={4} />}
            {personas.error && <ErrorState message={personas.error} onRetry={personas.reload} />}
            {!personas.loading && !personas.error && list.length === 0 && <EmptyState title="No personas available">Ask the administrator to load the demo personas.</EmptyState>}
            {list.length > 0 && (
              <fieldset className="choice-grid">
                <legend className="sr-only">Choose a profile</legend>
                {list.map((p) => (
                  <label key={p.id} className={`choice${choice === p.id ? " is-selected" : ""}`}>
                    <input type="radio" name="persona" value={p.id} checked={choice === p.id} onChange={() => setChoice(p.id)} />
                    <span className="choice__title">{p.name}</span>
                    <span className="choice__sub">{p.headline}</span>
                    <span className="choice__meta">
                      {money(p.hourly_rate_usd)}/hr · {p.skills.slice(0, 4).join(", ")}
                    </span>
                  </label>
                ))}
                <label className={`choice${choice === OWN ? " is-selected" : ""}`}>
                  <input type="radio" name="persona" value={OWN} checked={choice === OWN} onChange={() => setChoice(OWN)} />
                  <span className="choice__title">Use my own profile</span>
                  <span className="choice__sub">Start from a persona, then add your own work samples.</span>
                </label>
              </fieldset>
            )}
            {choice === OWN && (
              <div className="field">
                <label htmlFor="base">Start from</label>
                <select id="base" value={base} onChange={(e) => setBase(e.target.value)}>
                  <option value="">Choose a persona</option>
                  {list.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </section>
        )}

        {step === 1 && (
          <section aria-labelledby="s1">
            <h2 id="s1" className="h3">
              Connect a marketplace
            </h2>
            <fieldset className="choice-grid">
              <legend className="sr-only">Marketplace</legend>
              <label className={`choice${marketplace === "gigsim" ? " is-selected" : ""}`}>
                <input type="radio" name="marketplace" checked={marketplace === "gigsim"} onChange={() => setMarketplace("gigsim")} />
                <span className="choice__title">GigSim</span>
                <span className="choice__sub">A simulated marketplace. Nothing real is sent. Best for trying GigBid.</span>
              </label>
              <label className={`choice${marketplace === "upwork_live" ? " is-selected" : ""}`}>
                <input type="radio" name="marketplace" checked={marketplace === "upwork_live"} onChange={() => setMarketplace("upwork_live")} />
                <span className="choice__title">Upwork</span>
                <span className="choice__sub">Sign in on Upwork to let GigBid read jobs and send approved proposals.</span>
              </label>
            </fieldset>
            <p>
              <button type="button" className="btn" disabled={connect.busy} onClick={() => void connect.call()}>
                Connect Upwork
              </button>
            </p>
            <InlineError message={connect.error} />
          </section>
        )}

        {step === 2 && (
          <section aria-labelledby="s2">
            <h2 id="s2" className="h3">
              Add portfolio items
            </h2>
            <p className="muted">
              GigBid only cites evidence from your portfolio. {choice === OWN ? "Add at least one item." : "You can skip this and add items later."}
            </p>
            <form
              className="form"
              onSubmit={(e) => {
                e.preventDefault();
                void upload.call();
              }}
            >
              <div className="field">
                <label htmlFor="up-title">Title</label>
                <input id="up-title" required value={up.title} onChange={(e) => setUp({ ...up, title: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="up-kind">Type</label>
                <select id="up-kind" value={up.kind} onChange={(e) => setUp({ ...up, kind: e.target.value as Kind })}>
                  <option value="case_study">Case study</option>
                  <option value="repo">Repository</option>
                  <option value="review">Client review</option>
                  <option value="upload">Other</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="up-text">Text</label>
                <textarea id="up-text" required rows={5} value={up.text} onChange={(e) => setUp({ ...up, text: e.target.value })} placeholder="Paste the case study, README or review text." />
              </div>
              <InlineError message={upload.error} />
              <button type="submit" className="btn" disabled={upload.busy || !up.title.trim() || !up.text.trim()}>
                Upload item
              </button>
            </form>
            {uploaded.length > 0 && (
              <ul className="plain-list" aria-label="Uploaded items">
                {uploaded.map((t, i) => (
                  <li key={i}>Added: {t}</li>
                ))}
              </ul>
            )}
          </section>
        )}

        {step === 3 && (
          <section aria-labelledby="s3">
            <h2 id="s3" className="h3">
              Rates and Connects
            </h2>
            <div className="form form--grid">
              <div className="field">
                <label htmlFor="rate">Hourly rate (USD)</label>
                <input id="rate" type="number" min={1} step="1" value={hourly} onChange={(e) => setHourly(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="minp">Minimum project (USD)</label>
                <input id="minp" type="number" min={0} step="1" value={minProject} onChange={(e) => setMinProject(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="cb">Weekly Connects budget</label>
                <input id="cb" type="number" min={0} step="1" value={connects} onChange={(e) => setConnects(e.target.value)} />
                <span className="hint">GigBid will not recommend bids beyond this.</span>
              </div>
            </div>
          </section>
        )}

        {step === 4 && (
          <section aria-labelledby="s4">
            <h2 id="s4" className="h3">
              Save your first search
            </h2>
            <p className="muted">GigBid scouts this search on a schedule. Leave the name empty to skip.</p>
            <div className="form form--grid">
              <div className="field">
                <label htmlFor="sn">Name</label>
                <input id="sn" value={search.name} onChange={(e) => setSearch({ ...search, name: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="sq">Keywords</label>
                <input id="sq" value={search.query} onChange={(e) => setSearch({ ...search, query: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="sc">Category (optional)</label>
                <input id="sc" value={search.category} onChange={(e) => setSearch({ ...search, category: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="si">Check every (minutes)</label>
                <input id="si" type="number" min={5} value={search.interval} onChange={(e) => setSearch({ ...search, interval: e.target.value })} />
              </div>
            </div>
            <InlineError message={finish.error} />
          </section>
        )}

        <div className="wizard__nav">
          <button type="button" className="btn btn--ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>
            Back
          </button>
          {step < STEPS.length - 1 ? (
            <button type="button" className="btn btn--primary" disabled={!canNext} onClick={() => setStep(step + 1)}>
              Next
            </button>
          ) : (
            <button type="button" className="btn btn--primary" disabled={finish.busy || !personaId} onClick={() => void finish.call()}>
              {finish.busy ? "Saving..." : "Finish setup"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
