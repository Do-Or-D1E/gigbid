export type AppointmentStatus = 'new' | 'paid' | 'cancelled';

export interface Appointment {
  id: string;
  reference: string;
  status: AppointmentStatus;
  totalCents: number;
  createdAt: string;
}

export interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export function isPaid(x: Appointment): boolean {
  return x.status === 'paid' && x.totalCents > 0;
}

export function groupByStatus(items: Appointment[]): Record<AppointmentStatus, Appointment[]> {
  const out: Record<AppointmentStatus, Appointment[]> = { new: [], paid: [], cancelled: [] };
  for (const it of items) out[it.status].push(it);
  return out;
}

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}

export function paginate(items, page = 1, size = 20) {
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), total: items.length, page, size };
}
