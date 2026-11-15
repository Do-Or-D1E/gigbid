import { test, expect, type Page } from "@playwright/test";
import { bodyOf, mockApi } from "./helpers";

async function noHorizontalScroll(page: Page) {
  const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(over, "page must not scroll horizontally").toBeLessThanOrEqual(1);
}

test("inbox ranks jobs, shows risk and action, and scouting opens the live run", async ({ page }) => {
  const state = await mockApi(page);
  await page.goto("/inbox");
  const items = page.getByRole("list", { name: "Jobs" }).getByRole("listitem");
  await expect(items).toHaveCount(3);
  await expect(items.first()).toContainText("Migrate billing dashboard to React"); // highest fit first
  await expect(items.nth(1)).toContainText("Airflow pipeline review");
  await expect(items.nth(2)).toContainText("High risk");
  await expect(items.nth(2)).toContainText("Prompt injection found");
  await expect(items.first()).toContainText("Recommended: Bid");
  await expect(items.first()).toContainText("$1,800");

  await page.getByRole("button", { name: "Scout now" }).click();
  await expect(page.getByTestId("run-stream-panel")).toContainText("Scouting for new jobs");
  await expect(page.getByText("Run finished")).toBeVisible();
  expect(state.calls.some((c) => c.method === "POST" && c.path === "/api/scout")).toBe(true);
  await noHorizontalScroll(page);
});

test("inbox empty state explains how to scout", async ({ page }) => {
  await mockApi(page, { handlers: { "GET /api/jobs": () => ({ json: [] }) } });
  await page.goto("/inbox");
  await expect(page.getByRole("heading", { name: "No jobs yet" })).toBeVisible();
  await expect(page.getByText(/Choose Scout now/)).toBeVisible();
});

test("inbox error state offers a retry", async ({ page }) => {
  let n = 0;
  await mockApi(page, { handlers: { "GET /api/jobs": () => (n++ === 0 ? { status: 500, json: { detail: "Database is locked" } } : undefined) } });
  await page.goto("/inbox");
  await expect(page.getByRole("alert")).toContainText("Database is locked");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("list", { name: "Jobs" })).toBeVisible();
});

test("skip asks for a reason", async ({ page }) => {
  const state = await mockApi(page);
  await page.goto("/inbox");
  const card = page.getByRole("listitem").filter({ hasText: "Airflow pipeline review" });
  await card.getByRole("button", { name: "Skip" }).click();
  await card.getByLabel("Reason for skipping").fill("Rate too low");
  await card.getByRole("button", { name: "Confirm skip" }).click();
  expect(bodyOf(state, "POST", "/api/jobs/j-102/skip")).toEqual({ reason: "Rate too low" });
});

test("job detail shows the evidence matrix with hover evidence", async ({ page }) => {
  await mockApi(page);
  await page.goto("/jobs/j-100");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Migrate billing dashboard to React");
  const matrix = page.getByTestId("matrix");
  await expect(matrix).toContainText("React");
  await matrix.getByRole("button", { name: "Stripe dashboard case study" }).focus();
  await expect(page.getByRole("tooltip")).toContainText("Reduced churn reporting");
  await expect(page.getByRole("link", { name: "Open in studio" })).toHaveAttribute("href", "/studio/t-100");
  await expect(page.getByRole("button", { name: "Draft anyway" })).toBeVisible();
  await expect(page.getByRole("link", { name: "analyze" })).toBeVisible();
  await noHorizontalScroll(page);
});

test("pipeline board shows columns and links drafted cards to the studio", async ({ page }) => {
  await mockApi(page);
  await page.goto("/pipeline");
  for (const c of ["Drafted", "Submitted", "Viewed", "Replied", "Interview", "Hired", "Lost"]) {
    await expect(page.getByRole("heading", { name: new RegExp(`^${c}`) })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: /Migrate billing dashboard/ })).toHaveAttribute("href", "/studio/t-100");
  await noHorizontalScroll(page); // only the board itself scrolls
});

test("messages: scam signal is prominent and the reply can be approved", async ({ page }) => {
  const state = await mockApi(page, {
    handlers: { "POST /api/approvals/t-200/decision": () => ({ json: { run_id: "r-msg", thread_id: "t-200", status: "queued" } }) },
  });
  await page.goto("/messages");
  await page.getByRole("link", { name: /Airflow pipeline review/ }).click();
  await expect(page).toHaveURL(/\/messages\/t-200/);
  await expect(page.getByRole("alert").filter({ hasText: "Scam signal" })).toContainText("scam signal");
  await expect(page.getByRole("list", { name: "Proposed interview slots" })).toContainText("Tue 17 Nov, 10:00");
  await expect(page.getByRole("textbox", { name: "Reply" })).toHaveValue(/I keep all communication on the platform/);
  await page.getByRole("button", { name: "Approve and send" }).click();
  expect(bodyOf(state, "POST", "/api/approvals/t-200/decision")).toEqual({ action: "approve" });
  await noHorizontalScroll(page);
});

test("run viewer: timeline, per-node table, trace link and replay", async ({ page }) => {
  const state = await mockApi(page);
  await page.goto("/runs/r-1");
  await expect(page.getByTestId("run-timeline")).toContainText("Risk 12, no flags");
  await expect(page.getByTestId("per-node")).toContainText("scout");
  await expect(page.getByTestId("spans")).toContainText("risk.classify");

  await page.getByRole("button", { name: "Create public trace link" }).click();
  await expect(page.getByRole("link", { name: "Open full trace" })).toHaveAttribute("href", "https://trace.example.com/public/r-1");
  expect(state.calls.some((c) => c.path === "/api/runs/r-1/share")).toBe(true);

  await page.getByRole("button", { name: "Replay from here" }).first().click();
  await expect(page).toHaveURL(/\/runs\/r-2/);
  await noHorizontalScroll(page);
});

test("analytics renders charts and budget comparison", async ({ page }) => {
  await mockApi(page);
  await page.goto("/analytics");
  await expect(page.getByTestId("category-chart")).toContainText("web");
  await expect(page.getByRole("img", { name: "web reply rate 40%" })).toBeVisible();
  await expect(page.getByText("Over budget")).toBeVisible(); // 41.5 s against a 40 s budget
  await expect(page.getByText("Budget too low")).toBeVisible();
  await noHorizontalScroll(page);
});

test("settings: autonomy copy, save, memory, read-only system info", async ({ page }) => {
  const state = await mockApi(page);
  await page.goto("/settings");
  await expect(page.getByText(/never sends a proposal or message on its own/)).toBeVisible();
  await page.getByLabel("Weekly Connects budget").fill("120");
  await page.getByRole("radio", { name: /Skip low-fit jobs/ }).check();
  await page.getByRole("button", { name: "Save settings" }).click();
  expect(bodyOf(state, "PUT", "/api/settings")).toMatchObject({ autonomy: "auto_skip_low_fit", weekly_connects_budget: 120 });
  await expect(page.getByText("Open with the client's problem")).toBeVisible();
  await expect(page.getByText("An edit pattern becomes a style rule")).toBeVisible();
  await expect(page.getByTestId("system-info")).toContainText("hybrid");
  await expect(page.getByRole("button", { name: "Unhide API platform repo" })).toBeVisible();
  await noHorizontalScroll(page);
});

test("mobile layout: bottom navigation and no horizontal scroll on the studio", async ({ page, isMobile }) => {
  test.skip(!isMobile, "mobile only");
  await mockApi(page);
  await page.goto("/studio/t-100");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Migrate billing dashboard");
  await noHorizontalScroll(page);
  const nav = page.getByRole("navigation", { name: "Main" });
  const box = await nav.boundingBox();
  const vh = page.viewportSize()!.height;
  expect(box!.y + box!.height).toBeGreaterThan(vh - 4); // pinned to the bottom edge
});
