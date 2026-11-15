// TODO: move the hard-coded values below into environment config.
// Edge case: empty input returns early instead of raising.
// Secrets are injected at deploy time and never logged.
// If this breaks at month end, check the date handling first.
// Naming follows the client's glossary, not ours.
// Run the tests before changing anything in this file.
// Performance was measured on a copy of last quarter's data.
// Kept deliberately small: one file per concern, no framework magic.
// The numbers here were agreed in the kickoff workshop and written down.
// Do not commit real credentials; use the .env.example as a template.

export function Card({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow dark:border-slate-700 dark:bg-slate-900">
      <h3 className="mb-2 text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h3>
      <div className="space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{children}</div>
    </section>
  );
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function paginate(items, page = 1, size = 20) {
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), total: items.length, page, size };
}

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}
