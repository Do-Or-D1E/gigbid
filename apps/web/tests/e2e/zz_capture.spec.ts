// Captures screenshots of every screen (fixture data) for the demo video. Not part of the CI suite
// assertions; run with: npx playwright test zz_capture --project=chromium-desktop
import { test } from "@playwright/test";
import { mockApi } from "./helpers";

const OUT = "C:/Users/Administrator/Desktop/hci/tooltalk/gigbid-demo/public/shots";
const pages: [string, string][] = [
  ["01_inbox", "/inbox"],
  ["02_job", "/jobs/j-100"],
  ["03_studio", "/studio/t-100"],
  ["05_pipeline", "/pipeline"],
  ["06_messages", "/messages/t-200"],
  ["07_run", "/runs/r-1"],
  ["08_analytics", "/analytics"],
  ["09_settings", "/settings"],
];

test("capture screens", async ({ page }) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await mockApi(page);
  for (const [name, path] of pages) {
    await page.goto(path);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/${name}.png` });
    if (name === "03_studio") {
      const claim = page.locator("[data-claim-id], [role=button][aria-describedby]").first();
      if (await claim.count()) {
        await claim.focus();
        await page.waitForTimeout(600);
        await page.screenshot({ path: `${OUT}/04_evidence.png` });
      }
    }
  }
  state.health = (await import("./fixtures/health_down.json", { with: { type: "json" } })).default;
  await page.goto("/inbox");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/10_degraded.png` });
});
