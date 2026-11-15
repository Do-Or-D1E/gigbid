import { test, expect } from "@playwright/test";
import { bodyOf, openStudio } from "./helpers";

test("reject stays disabled until a reason is typed, then sends it", async ({ page }) => {
  const state = await openStudio(page);
  const reject = page.getByRole("button", { name: "Reject" });

  await expect(reject).toBeDisabled();
  await page.getByLabel("Reason for rejecting").fill("   ");
  await expect(reject).toBeDisabled(); // whitespace is not a reason

  await page.getByLabel("Reason for rejecting").fill("Budget is too low for this scope");
  await expect(reject).toBeEnabled();
  await reject.click();

  expect(bodyOf(state, "POST", "/api/approvals/t-100/decision")).toEqual({ action: "reject", reason: "Budget is too low for this scope" });
  await expect(page.getByText("Run finished")).toBeVisible();
  await expect(page.getByText(/Rejected: Budget is too low/)).toBeVisible();
});
