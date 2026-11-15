import { test, expect } from "@playwright/test";
import { bodyOf, openStudio } from "./helpers";

test("approving a proposal sends the decision and shows the live run", async ({ page }) => {
  const state = await openStudio(page);

  // the human gate: exact payload, Connects cost and balance are visible before approving
  await expect(page.getByTestId("preview-payload")).toContainText('"amount": 1800');
  await expect(page.getByTestId("connects")).toContainText("16");
  await expect(page.getByTestId("connects")).toContainText("64");
  await expect(page.getByText("The proposal names a start date.")).toBeVisible();

  await page.getByRole("button", { name: "Approve and send" }).click();

  expect(bodyOf(state, "POST", "/api/approvals/t-100/decision")).toEqual({ action: "approve" });
  // live stream panel: nodes with latency, tokens and summaries
  const timeline = page.getByTestId("run-timeline");
  await expect(timeline).toContainText("compliance");
  await expect(timeline).toContainText("Policy check passed");
  await expect(timeline).toContainText("210 tokens");
  await expect(timeline).toContainText("Submitted to GigSim");
  await expect(page.getByText("Run finished")).toBeVisible();

  // after the run ends the approval is reloaded and the result is shown
  await expect(page.getByTestId("submit-result")).toContainText("Submitted");
  await expect(page.getByText("Approved. The proposal was submitted.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve and send" })).toHaveCount(0);
});
