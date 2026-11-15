import { test, expect } from "@playwright/test";
import { openStudio } from "./helpers";

test("hovering a claim shows its evidence", async ({ page, isMobile }) => {
  test.skip(!!isMobile, "touch devices have no hover; the keyboard test covers them");
  await openStudio(page);
  const claim = page.getByTestId("claim-c1");
  await expect(claim).toHaveText(/Stripe subscription dashboard in React/);
  await claim.hover();
  const tip = page.getByRole("tooltip");
  await expect(tip).toBeVisible();
  await expect(tip).toContainText("Supported");
  await expect(tip).toContainText("Stripe dashboard case study");
  await expect(tip).toContainText("Reduced churn reporting from 5 hours to 2 hours");
  await page.mouse.move(5, 5);
  await expect(tip).toHaveCount(0);
});

test("keyboard focus shows evidence and Escape closes it", async ({ page }) => {
  await openStudio(page);
  const claim = page.getByTestId("claim-c2");
  await expect(claim).toBeVisible();

  // reachable with Tab: focus the previous claim, then Tab forward
  await page.getByTestId("claim-c1").focus();
  await page.keyboard.press("Tab");
  await expect(claim).toBeFocused();
  const tip = page.getByRole("tooltip");
  await expect(tip).toBeVisible();
  await expect(tip).toContainText("Partly supported");
  await expect(tip).toContainText("API platform repo");
  await expect(tip).toContainText("1.4M requests per day");
  await expect(claim).toHaveAttribute("aria-describedby", /.+/);

  await page.keyboard.press("Escape");
  await expect(tip).toHaveCount(0);
});

test("a claim missing from the text is listed below the editor with its status", async ({ page }) => {
  await openStudio(page);
  const list = page.getByTestId("unmatched-claims");
  await expect(list).toContainText("won a design award in 2021");
  await list.getByRole("button", { name: /won a design award/ }).focus();
  await expect(page.getByRole("tooltip")).toContainText("No evidence found for this claim.");
});

test("critic notes appear next to the paragraph they refer to", async ({ page }) => {
  await openStudio(page);
  await expect(page.getByTestId("paragraph-0")).toContainText("The opening is generic");
  await expect(page.getByTestId("paragraph-2")).toContainText("Say which milestone");
  await expect(page.getByTestId("paragraph-1")).not.toContainText("Critic");
});
