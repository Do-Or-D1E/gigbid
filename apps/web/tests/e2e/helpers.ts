import { readFileSync } from "node:fs";
import type { Page, Request, Route } from "@playwright/test";

/** Load a JSON fixture from tests/e2e/fixtures. Returns a fresh copy each time so tests can mutate it. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function fx(name: string): any {
  return JSON.parse(readFileSync(new URL(`./fixtures/${name}.json`, import.meta.url), "utf8"));
}

export interface SseEvent {
  event: string;
  data: Record<string, unknown>;
}

/** Build a text/event-stream body. Each data line is JSON {id, ts, kind, node, payload}. */
export function sseBody(events: SseEvent[]): string {
  return (
    events
      .map((e, i) => {
        const data = { id: i + 1, ts: new Date().toISOString(), kind: e.event, ...e.data };
        return `id: ${i + 1}\nevent: ${e.event}\ndata: ${JSON.stringify(data)}\n\n`;
      })
      .join("") + "\n"
  );
}

export const RUN_EVENTS: SseEvent[] = [
  { event: "queued", data: { node: null, payload: {} } },
  { event: "start", data: { node: "compliance", payload: { node: "compliance", event: "start" } } },
  { event: "end", data: { node: "compliance", payload: { node: "compliance", event: "end", latency_s: 0.42, tokens: 210, summary: "Policy check passed" } } },
  { event: "start", data: { node: "submit", payload: { node: "submit", event: "start" } } },
  { event: "end", data: { node: "submit", payload: { node: "submit", event: "end", latency_s: 0.8, summary: "Submitted to GigSim" } } },
  { event: "end", data: { node: null, payload: {} } },
];

export interface MockState {
  /** every request that hit /api, in order */
  calls: { method: string; path: string; body: unknown }[];
  /** override or extend responses: key is "METHOD /api/path" (query ignored) */
  handlers: Record<string, (req: Request, state: MockState) => { status?: number; json?: unknown; body?: string; contentType?: string } | undefined>;
  health: unknown;
  approval: ReturnType<typeof fx>;
  user: ReturnType<typeof fx>;
  decided: boolean;
}

export function bodyOf(state: MockState, method: string, path: string): any { // eslint-disable-line @typescript-eslint/no-explicit-any
  const c = [...state.calls].reverse().find((x) => x.method === method && x.path === path);
  return c?.body;
}

/**
 * Mock the whole backend with page.route(). Nothing here talks to a real server or an LLM.
 * Pass `signedIn: false` to test login.
 */
export async function mockApi(page: Page, opts: { signedIn?: boolean; handlers?: MockState["handlers"] } = {}): Promise<MockState> {
  const state: MockState = {
    calls: [],
    handlers: opts.handlers ?? {},
    health: fx("health_up"),
    approval: fx("approval"),
    user: fx("user"),
    decided: false,
  };

  if (opts.signedIn !== false) {
    await page.addInitScript(() => {
      try {
        localStorage.setItem("gigbid.token", "test-token");
      } catch {
        /* ignore */
      }
    });
  }

  await page.route("**/api/**", async (route: Route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method();
    let body: unknown = undefined;
    try {
      body = req.postDataJSON();
    } catch {
      body = undefined;
    }
    state.calls.push({ method, path, body });

    const custom = state.handlers[`${method} ${path}`];
    if (custom) {
      const r = custom(req, state);
      if (r) {
        return route.fulfill({ status: r.status ?? 200, contentType: r.contentType ?? "application/json", body: r.body ?? JSON.stringify(r.json ?? {}) });
      }
    }

    const json = (data: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });

    if (path.endsWith("/stream")) {
      return route.fulfill({ status: 200, contentType: "text/event-stream", headers: { "cache-control": "no-cache" }, body: sseBody(RUN_EVENTS) });
    }
    const key = `${method} ${path}`;
    switch (true) {
      case key === "GET /api/health":
        return json(state.health);
      case key === "GET /api/auth/me":
        return json(state.user);
      case key === "POST /api/auth/login":
      case key === "POST /api/auth/register":
        return json({ token: "test-token", user: state.user });
      case key === "GET /api/personas":
        return json(fx("personas"));
      case key === "POST /api/portfolio/upload":
        return json({ item_id: "up1", type: "case_study", title: (body as { title: string }).title, hidden: false });
      case key === "POST /api/onboarding":
        state.user = fx("user");
        return json(state.user);
      case key === "GET /api/jobs":
        return json(fx("jobs"));
      case key === "GET /api/jobs/j-100":
        return json(fx("job_detail"));
      case key === "POST /api/scout":
        return json({ queued: ["r-scout"], duplicates: [] });
      case /^POST \/api\/jobs\/[^/]+\/analyze$/.test(key):
      case /^POST \/api\/jobs\/[^/]+\/draft$/.test(key):
        return json({ run_id: "r-1", thread_id: "t-100", status: "queued" });
      case /^POST \/api\/jobs\/[^/]+\/skip$/.test(key):
        return json(fx("jobs")[1]);
      case key === "GET /api/approvals/t-100":
        return json(state.approval);
      case key === "POST /api/approvals/t-100/decision": {
        const action = (body as { action: string }).action;
        state.decided = true;
        if (action === "approve") state.approval = { ...state.approval, status: "approved", decision: { action } };
        else if (action === "reject") state.approval = { ...state.approval, status: "rejected", decision: { action, reason: (body as { reason?: string }).reason } };
        else {
          // an edit is re-checked and comes back as a new pending approval
          const next = fx("approval");
          next.payload.draft.cover_letter = (body as { edited_cover_letter: string }).edited_cover_letter;
          next.payload.draft.version = 2;
          state.approval = next;
        }
        return json({ run_id: "r-dec", thread_id: "t-100", status: "queued" });
      }
      case key === "POST /api/proposals/t-100/regenerate":
        return json({ text: "Rewritten paragraph with no unsupported claims.", removed: ["won a design award in 2021"] });
      case key === "GET /api/pipeline":
        return json(fx("pipeline"));
      case key === "POST /api/pipeline/sync":
        return json({ synced: 2 });
      case key === "GET /api/messages/threads":
        return json(fx("threads"));
      case key === "GET /api/messages/threads/t-200":
        return json(fx("thread_detail"));
      case key === "GET /api/runs":
        return json([fx("run_detail")]);
      case key === "GET /api/runs/r-1":
        return json(fx("run_detail"));
      case key === "GET /api/runs/r-1/history":
        return json(fx("history"));
      case key === "POST /api/runs/r-1/share":
        return json({ url: "https://trace.example.com/public/r-1" });
      case /^POST \/api\/runs\/r-1\/replay\//.test(key):
        return json({ run_id: "r-2", thread_id: "t-100", status: "queued" });
      case key === "GET /api/runs/r-2":
        return json({ ...fx("run_detail"), run_id: "r-2" });
      case key === "GET /api/runs/r-2/history":
        return json([]);
      case key === "GET /api/runs/r-dec":
        return json({ ...fx("run_detail"), run_id: "r-dec", kind: "decision", metrics: { submitted: true } });
      case key === "GET /api/analytics":
        return json(fx("analytics"));
      case key === "GET /api/settings":
        return json(fx("settings"));
      case key === "PUT /api/settings":
        return json({ ...fx("settings"), ...(body as object) });
      case key === "GET /api/memory":
        return json(fx("memory"));
      case key === "GET /api/portfolio/items":
        return json(fx("portfolio"));
      default:
        return json({ detail: `No mock for ${key}` }, 404);
    }
  });

  return state;
}

/** Shorthand: open the proposal studio with the default fixture. */
export async function openStudio(page: Page, handlers?: MockState["handlers"]) {
  const state = await mockApi(page, { handlers });
  await page.goto("/studio/t-100");
  await page.getByRole("heading", { name: "Migrate billing dashboard to React", level: 1 }).waitFor();
  return state;
}
