import { useEffect, useState } from 'react';

export function MatterList({ status }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/matters?status=${status}`)
      .then((r) => r.json())
      .then((data) => { if (!cancelled) { setItems(data); setLoading(false); } });
    return () => { cancelled = true; };
  }, [status]);

  if (loading) return <p>Loading...</p>;
  return (
    <ul>
      {items.map((it) => (
        <li key={it.id}>{it.reference} - {it.status}</li>
      ))}
    </ul>
  );
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}

export function paginate(items, page = 1, size = 20) {
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), total: items.length, page, size };
}
