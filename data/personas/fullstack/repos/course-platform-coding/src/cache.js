
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL ?? 'redis://localhost:6379');

export async function cached(key, ttlSeconds, loader) {
  const hit = await redis.get(key);
  if (hit) return JSON.parse(hit);
  const fresh = await loader();
  await redis.set(key, JSON.stringify(fresh), 'EX', ttlSeconds);
  return fresh;
}

export async function rateLimit(ip, limit = 100) {
  const k = `rl:${ip}`;
  const n = await redis.incr(k);
  if (n === 1) await redis.expire(k, 60);
  return n <= limit;
}

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function paginate(items, page = 1, size = 20) {
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), total: items.length, page, size };
}
