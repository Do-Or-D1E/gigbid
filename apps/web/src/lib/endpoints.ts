/** Thin typed helpers over the generated client. One function per backend operation used by the UI. */
import { api, unwrap } from "./client";
import type { components } from "./api/schema";
import type { AnyRec } from "./types";

type S = components["schemas"];

export const endpoints = {
  login: (body: S["LoginIn"]) => unwrap(api.POST("/api/auth/login", { body })),
  register: (body: S["RegisterIn"]) => unwrap(api.POST("/api/auth/register", { body })),
  me: () => unwrap(api.GET("/api/auth/me")),
  personas: () => unwrap(api.GET("/api/personas")),
  onboard: (body: S["OnboardingIn"]) => unwrap(api.POST("/api/onboarding", { body })),

  settings: () => unwrap(api.GET("/api/settings")),
  saveSettings: (body: S["SettingsIn"]) => unwrap(api.PUT("/api/settings", { body })),
  addSearch: (body: S["SavedSearchIn"]) => unwrap(api.POST("/api/settings/searches", { body })),
  deleteSearch: (search_id: number) =>
    unwrap(api.DELETE("/api/settings/searches/{search_id}", { params: { path: { search_id } } })),
  memory: () => unwrap(api.GET("/api/memory")),
  deleteMemory: (kind: string, key: string) =>
    unwrap(api.DELETE("/api/memory/{kind}/{key}", { params: { path: { kind, key } } })),

  portfolio: () => unwrap(api.GET("/api/portfolio/items")),
  hideItem: (item_id: string) => unwrap(api.POST("/api/portfolio/items/{item_id}/hide", { params: { path: { item_id } } })),
  unhideItem: (item_id: string) =>
    unwrap(api.POST("/api/portfolio/items/{item_id}/unhide", { params: { path: { item_id } } })),
  upload: (body: S["UploadIn"]) => unwrap(api.POST("/api/portfolio/upload", { body })),

  jobs: (q: { status?: string; action?: string; q?: string }) =>
    unwrap(api.GET("/api/jobs", { params: { query: { status: q.status || undefined, action: q.action || undefined, q: q.q || undefined } } })),
  job: (job_id: string) => unwrap(api.GET("/api/jobs/{job_id}", { params: { path: { job_id } } })),
  analyze: (job_id: string) => unwrap(api.POST("/api/jobs/{job_id}/analyze", { params: { path: { job_id } } })),
  draft: (job_id: string) => unwrap(api.POST("/api/jobs/{job_id}/draft", { params: { path: { job_id } } })),
  skip: (job_id: string, reason?: string) =>
    unwrap(api.POST("/api/jobs/{job_id}/skip", { params: { path: { job_id } }, body: { reason: reason?.trim() || "not interested" } })),
  scout: () => unwrap(api.POST("/api/scout")) as Promise<AnyRec>,

  approval: (thread_id: string) => unwrap(api.GET("/api/approvals/{thread_id}", { params: { path: { thread_id } } })),
  decide: (thread_id: string, body: S["DecisionIn"]) =>
    unwrap(api.POST("/api/approvals/{thread_id}/decision", { params: { path: { thread_id } }, body })),
  regenerate: (thread_id: string, body: S["RegenerateIn"]) =>
    unwrap(api.POST("/api/proposals/{thread_id}/regenerate", { params: { path: { thread_id } }, body })),

  pipeline: () => unwrap(api.GET("/api/pipeline")),
  syncPipeline: () => unwrap(api.POST("/api/pipeline/sync")) as Promise<AnyRec>,

  threads: () => unwrap(api.GET("/api/messages/threads")),
  thread: (thread_id: string) => unwrap(api.GET("/api/messages/threads/{thread_id}", { params: { path: { thread_id } } })),
  suggest: (thread_id: string) =>
    unwrap(api.POST("/api/messages/threads/{thread_id}/suggest", { params: { path: { thread_id } } })),

  runs: (limit = 50) => unwrap(api.GET("/api/runs", { params: { query: { limit } } })),
  run: (run_id: string) => unwrap(api.GET("/api/runs/{run_id}", { params: { path: { run_id } } })),
  runHistory: (run_id: string) => unwrap(api.GET("/api/runs/{run_id}/history", { params: { path: { run_id } } })),
  replay: (run_id: string, checkpoint_id: string) =>
    unwrap(api.POST("/api/runs/{run_id}/replay/{checkpoint_id}", { params: { path: { run_id, checkpoint_id } } })),
  share: (run_id: string) => unwrap(api.POST("/api/runs/{run_id}/share", { params: { path: { run_id } } })),

  analytics: () => unwrap(api.GET("/api/analytics")),
  health: () => unwrap(api.GET("/api/health")),
  upworkStart: () => unwrap(api.GET("/api/oauth/upwork/start")) as Promise<AnyRec>,
};
