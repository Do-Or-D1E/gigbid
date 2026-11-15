import { test, expect } from "@playwright/test";
import { fx, mockApi } from "./helpers";

const TEXT = "Marketplace unavailable - GigBid has queued your work and will resume automatically.";

test("health reports marketplace down: persistent banner with detail", async ({ page }) => {
  const state = await mockApi(page);
  state.health = fx("health_down");
  await page.goto("/inbox");
  const banner = page.getByTestId("marketplace-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText(TEXT);
  await expect(banner).toContainText("GigSim returned 503");
  // it stays while navigating
  await page.getByRole("link", { name: "Pipeline" }).first().click();
  await expect(banner).toBeVisible();
});

test("banner clears when the next health poll says up (15 s polling)", async ({ page }) => {
  await page.clock.install();
  const state = await mockApi(page);
  state.health = fx("health_down");
  await page.goto("/inbox");
  await expect(page.getByTestId("marketplace-banner")).toBeVisible();
  state.health = fx("health_up");
  await page.clock.fastForward(16_000);
  await expect(page.getByTestId("marketplace-banner")).toHaveCount(0);
  const polls = state.calls.filter((c) => c.path === "/api/health").length;
  expect(polls).toBeGreaterThanOrEqual(2);
});

test("a 503 from the sync endpoint raises the same banner", async ({ page }) => {
  await mockApi(page, { handlers: { "POST /api/pipeline/sync": () => ({ status: 503, json: { detail: "Marketplace unavailable: connection refused" } }) } });
  await page.goto("/pipeline");
  await expect(page.getByTestId("marketplace-banner")).toHaveCount(0);
  await page.getByRole("button", { name: "Sync" }).click();
  await expect(page.getByTestId("marketplace-banner")).toContainText(TEXT);
  await expect(page.getByTestId("marketplace-banner")).toContainText("connection refused");
});

test("messages show an unavailable state on 503", async ({ page }) => {
  await mockApi(page, { handlers: { "GET /api/messages/threads": () => ({ status: 503, json: { detail: "Marketplace unavailable" } }) } });
  await page.goto("/messages");
  await expect(page.getByRole("heading", { name: "Messages are unavailable" })).toBeVisible();
  await expect(page.getByTestId("marketplace-banner")).toContainText(TEXT);
});
