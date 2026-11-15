import Stripe from 'stripe';

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

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}
