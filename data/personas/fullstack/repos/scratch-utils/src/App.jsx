import { NextResponse } from 'next/server';

export function Card({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow dark:border-slate-700 dark:bg-slate-900">
      <h3 className="mb-2 text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3>
      <div className="space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{children}</div>
    </section>
  );
}

export async function GET(req) {
  const { searchParams } = new URL(req.url);
  const page = Number(searchParams.get('page') ?? '1');
  const rows = await listPage(page, 20);
  return NextResponse.json({ page, rows }, { headers: { 'Cache-Control': 's-maxage=30, stale-while-revalidate=120' } });
}

export async function POST(req) {
  const body = await req.json();
  if (!body.name) {
    return NextResponse.json({ error: 'name is required' }, { status: 400 });
  }
  const created = await createBooking(body);
  return NextResponse.json(created, { status: 201 });
}

export const revalidate = 60;

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}
