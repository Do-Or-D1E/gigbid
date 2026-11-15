import { test, expect } from "@playwright/test";
import { bodyOf, fx, mockApi } from "./helpers";

test("onboarding: sign in, choose persona, set rates, finish", async ({ page }) => {
  const state = await mockApi(page, { signedIn: false });
  state.user = fx("user_new");

  await page.goto("/inbox");
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("Email").fill("dana@example.com");
  await page.getByLabel("Password").fill("correct horse");
  await page.getByRole("button", { name: "Sign in" }).last().click();

  // not onboarded yet -> wizard
  await expect(page).toHaveURL(/\/onboarding/);
  await expect(page.getByRole("heading", { name: /Set up GigBid/ })).toBeVisible();

  // step 1: profile (Next is disabled until a persona is picked)
  await expect(page.getByRole("button", { name: "Next" })).toBeDisabled();
  await page.getByRole("radio", { name: /Maya Chen/ }).check();
  await page.getByRole("button", { name: "Next" }).click();

  // step 2: marketplace, GigSim is the default
  await expect(page.getByRole("radio", { name: /GigSim/ })).toBeChecked();
  await expect(page.getByRole("button", { name: "Connect Upwork" })).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();

  // step 3: portfolio upload
  await page.getByLabel("Title").fill("Billing dashboard");
  await page.getByLabel("Text").fill("Built a React billing dashboard with Stripe.");
  await page.getByRole("button", { name: "Upload item" }).click();
  await expect(page.getByText("Added: Billing dashboard")).toBeVisible();
  expect(bodyOf(state, "POST", "/api/portfolio/upload")).toMatchObject({ title: "Billing dashboard", kind: "case_study" });
  await page.getByRole("button", { name: "Next" }).click();

  // step 4: rates are prefilled from the persona
  await expect(page.getByLabel("Hourly rate (USD)")).toHaveValue("65");
  await page.getByLabel("Weekly Connects budget").fill("100");
  await page.getByRole("button", { name: "Next" }).click();

  // step 5: first saved search, then finish
  await page.getByLabel("Name").fill("React dashboards");
  await page.getByLabel("Keywords").fill("react dashboard");
  await page.getByRole("button", { name: "Finish setup" }).click();

  await expect(page).toHaveURL(/\/inbox/);
  expect(bodyOf(state, "POST", "/api/onboarding")).toMatchObject({
    persona_id: "p-fullstack",
    marketplace: "gigsim",
    hourly_rate_usd: 65,
    weekly_connects_budget: 100,
    saved_search: { name: "React dashboards", query: "react dashboard" },
  });
  await expect(page.getByRole("heading", { name: "Job inbox" })).toBeVisible();
});

test("login shows the server error", async ({ page }) => {
  await mockApi(page, { signedIn: false, handlers: { "POST /api/auth/login": () => ({ status: 401, json: { detail: "Wrong email or password." } }) } });
  await page.goto("/login");
  await page.getByLabel("Email").fill("a@b.co");
  await page.getByLabel("Password").fill("nope");
  await page.getByRole("button", { name: "Sign in" }).last().click();
  await expect(page.getByRole("alert").filter({ hasText: "Wrong email" })).toBeVisible();
});
