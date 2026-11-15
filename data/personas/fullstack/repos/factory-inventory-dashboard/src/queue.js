import amqp from 'amqplib';

const QUEUE = 'stock-alerts';

export async function publishAlert(payload) {
  const conn = await amqp.connect(process.env.AMQP_URL);
  const ch = await conn.createChannel();
  await ch.assertQueue(QUEUE, { durable: true });
  ch.sendToQueue(QUEUE, Buffer.from(JSON.stringify(payload)), { persistent: true });
  await ch.close();
  await conn.close();
}

export async function consume(handler) {
  const conn = await amqp.connect(process.env.AMQP_URL);
  const ch = await conn.createChannel();
  await ch.assertQueue(QUEUE, { durable: true });
  ch.prefetch(10);
  ch.consume(QUEUE, async (msg) => {
    if (!msg) return;
    try { await handler(JSON.parse(msg.content.toString())); ch.ack(msg); } catch { ch.nack(msg, false, false); }
  });
}

export function paginate(items, page = 1, size = 20) {
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), total: items.length, page, size };
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}
