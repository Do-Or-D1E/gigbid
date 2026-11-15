/**
 * Hand-written wrapper around the generated openapi-fetch client.
 * - adds the Authorization header (token kept in localStorage)
 * - adds X-Trace-Id (a new random id for each user action: click / submit / Enter)
 * - normalises errors into ApiError and broadcasts 401 / 503 situations
 */
import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./api/schema";

const TOKEN_KEY = "gigbid.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}
export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: session only */
  }
}

export function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  return Math.random().toString(16).slice(2, 10) + Date.now().toString(16);
}

let currentTrace = randomId();
export function currentTraceId(): string {
  return currentTrace;
}
if (typeof document !== "undefined") {
  const rotate = () => {
    currentTrace = randomId();
  };
  document.addEventListener("click", rotate, true);
  document.addEventListener("submit", rotate, true);
  document.addEventListener("keydown", (e) => (e.key === "Enter" ? rotate() : undefined), true);
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Something went wrong.";
}

function detailToText(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? `${(d as { loc?: unknown[] }).loc?.slice(1).join(".") ?? ""} ${(d as { msg: string }).msg}`.trim() : String(d)))
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    const o = detail as Record<string, unknown>;
    if (typeof o.message === "string") return o.message;
    if (typeof o.detail === "string") return o.detail;
  }
  if (status === 0) return "Cannot reach the GigBid server. Check your connection.";
  if (status === 401) return "Your session has expired. Sign in again.";
  if (status === 404) return "Not found.";
  if (status === 503) return "Marketplace unavailable.";
  return `Request failed (${status}).`;
}

type Listener = (status: number, detail: string) => void;
const listeners = new Set<Listener>();
export function onApiProblem(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

const middleware: Middleware = {
  onRequest({ request }) {
    const token = getToken();
    if (token && !request.headers.has("Authorization")) request.headers.set("Authorization", `Bearer ${token}`);
    request.headers.set("X-Trace-Id", currentTrace);
    return request;
  },
};

export const api = createClient<paths>({ baseUrl: "" });
api.use(middleware);

type Result<T> = { data?: T; error?: unknown; response: Response };

/** Unwrap an openapi-fetch result: return data or throw ApiError. */
export async function unwrap<T>(p: Promise<Result<T>>, opts: { path?: string } = {}): Promise<T> {
  let res: Result<T>;
  try {
    res = await p;
  } catch (e) {
    throw new ApiError(0, detailToText(null, 0), e);
  }
  if (res.error !== undefined || !res.response.ok) {
    const status = res.response.status;
    const detail = (res.error as { detail?: unknown } | undefined)?.detail ?? res.error;
    const msg = detailToText(detail, status);
    listeners.forEach((l) => l(status, msg));
    void opts;
    throw new ApiError(status, msg, detail);
  }
  return res.data as T;
}

/** Same as unwrap but for endpoints with empty (204 / non-JSON) bodies. */
export async function unwrapVoid(p: Promise<Result<unknown>>): Promise<void> {
  await unwrap(p).catch((e) => {
    if (e instanceof ApiError) throw e;
    throw e;
  });
}

export function runStreamUrl(runId: string, after?: number): string {
  const q = new URLSearchParams();
  const t = getToken();
  if (t) q.set("token", t);
  if (after) q.set("after", String(after));
  return `/api/runs/${encodeURIComponent(runId)}/stream?${q.toString()}`;
}
