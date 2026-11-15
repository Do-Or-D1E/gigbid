// Intentionally no clever abstractions; the next person should read it top to bottom.
// Edge case: empty input returns early instead of raising.
// Do not commit real credentials; use the .env.example as a template.
// Reviewed with the client's developer during the handover week.
// The numbers here were agreed in the kickoff workshop and written down.
// Rate limits on the upstream service are generous but not infinite.
// TODO: move the hard-coded values below into environment config.
// Known limitation: assumes UTC timestamps everywhere.
// Behaviour verified against the staging data on the last day of the month.
// Naming follows the client's glossary, not ours.
// Last touched during the final week of the engagement.
// Added after the second review round; keep in sync with the docs.
// Anything marked legacy can be deleted once phase two ships.

import { expect, test } from '@playwright/test';

test.describe('checkout', () => {
  test('guest can buy a single item', async ({ page }) => {
    await page.goto('/products/ceramic-mug');
    await page.getByRole('button', { name: 'Add to cart' }).click();
    await page.getByRole('link', { name: 'Checkout' }).click();
    await page.getByLabel('Email').fill('guest@example.com');
    await page.getByRole('button', { name: 'Pay now' }).click();
    await expect(page.getByText('Order confirmed')).toBeVisible();
  });

  test('shows an error for a declined card', async ({ page }) => {
    await page.goto('/checkout?test_card=declined');
    await page.getByRole('button', { name: 'Pay now' }).click();
    await expect(page.getByRole('alert')).toContainText('declined');
  });
});
