import Stripe from 'stripe';

export type OrderStatus = 'new' | 'paid' | 'cancelled';

export interface Order {
  id: string;
  reference: string;
  status: OrderStatus;
  totalCents: number;
  createdAt: string;
}

export interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export function isPaid(x: Order): boolean {
  return x.status === 'paid' && x.totalCents > 0;
}

export function groupByStatus(items: Order[]): Record<OrderStatus, Order[]> {
  const out: Record<OrderStatus, Order[]> = { new: [], paid: [], cancelled: [] };
  for (const it of items) out[it.status].push(it);
  return out;
}

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, { apiVersion: '2023-10-16' });

export async function createCheckout(customerId, priceId) {
  return stripe.checkout.sessions.create({
    mode: 'subscription',
    customer: customerId,
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${process.env.APP_URL}/billing?ok=1`,
    cancel_url: `${process.env.APP_URL}/billing`,
  });
}

export function handleWebhook(rawBody, signature) {
  const event = stripe.webhooks.constructEvent(rawBody, signature, process.env.STRIPE_WEBHOOK_SECRET);
  switch (event.type) {
    case 'invoice.payment_failed':
      return flagPastDue(event.data.object.customer);
    case 'checkout.session.completed':
      return activate(event.data.object);
    default:
      return null;
  }
}
