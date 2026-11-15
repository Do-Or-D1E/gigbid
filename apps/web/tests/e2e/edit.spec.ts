import { test, expect } from "@playwright/test";
import { bodyOf, openStudio } from "./helpers";

test("editing a draft sends edited_cover_letter and shows the re-checked version", async ({ page }) => {
  const state = await openStudio(page);
  const save = page.getByRole("button", { name: "Save edit" });
  const approve = page.getByRole("button", { name: "Approve and send" });

  await expect(save).toBeDisabled();
  await expect(approve).toBeEnabled();

  // edit the third paragraph
  const third = page.getByTestId("paragraph-2");
  await third.getByRole("button", { name: "Edit paragraph" }).click();
  await page.getByLabel("Edit paragraph 3").fill("I can start next week and deliver the invoice export milestone within two weeks.");

  // an unsaved edit must be saved (and re-checked) before approval
  await expect(save).toBeEnabled();
  await expect(approve).toBeDisabled();
  await save.click();

  const sent = bodyOf(state, "POST", "/api/approvals/t-100/decision");
  expect(sent.action).toBe("edit");
  expect(sent.edited_cover_letter).toContain("invoice export milestone");
  expect(sent.edited_cover_letter).toContain("I built a Stripe subscription dashboard"); // other paragraphs kept
  expect(sent.edited_cover_letter.split("\n\n")).toHaveLength(3);

  await expect(page.getByText("Your edit was re-checked by Compliance")).toBeVisible();
  await expect(page.getByTestId("paragraph-2")).toContainText("invoice export milestone");
  await expect(save).toBeDisabled();
  await expect(approve).toBeEnabled();
});

test("regenerate a paragraph then use the new text", async ({ page }) => {
  const state = await openStudio(page);
  const second = page.getByTestId("paragraph-1");
  await second.getByRole("button", { name: "Regenerate paragraph" }).click();
  await second.getByLabel("Instruction (optional)").fill("shorter");
  await second.getByRole("button", { name: "Generate new text" }).click();
  await expect(second.getByText("Rewritten paragraph with no unsupported claims.")).toBeVisible();
  expect(bodyOf(state, "POST", "/api/proposals/t-100/regenerate")).toEqual({ paragraph_index: 1, instruction: "shorter" });
  await second.getByRole("button", { name: "Use this text" }).click();
  await expect(page.getByRole("button", { name: "Save edit" })).toBeEnabled();
});
