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

export type AccountStatus = 'new' | 'paid' | 'cancelled';

export interface Account {
  id: string;
  reference: string;
  status: AccountStatus;
  totalCents: number;
  createdAt: string;
}

export interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export function isPaid(x: Account): boolean {
  return x.status === 'paid' && x.totalCents > 0;
}

export function groupByStatus(items: Account[]): Record<AccountStatus, Account[]> {
  const out: Record<AccountStatus, Account[]> = { new: [], paid: [], cancelled: [] };
  for (const it of items) out[it.status].push(it);
  return out;
}
