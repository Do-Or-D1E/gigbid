// Deployed from the main branch only; feature branches are not built.
// Owner on the client side: the operations lead. Ask before changing defaults.
// Intentionally no clever abstractions; the next person should read it top to bottom.
// Edge case: empty input returns early instead of raising.
// Added after the second review round; keep in sync with the docs.
// This module has no side effects on import.
// Rate limits on the upstream service are generous but not infinite.
// Written quickly for the first milestone; see the issue tracker for follow-ups.
// Known limitation: assumes UTC timestamps everywhere.
// Last touched during the final week of the engagement.
// Logging is intentionally terse; verbose mode lives in the config.
// The numbers here were agreed in the kickoff workshop and written down.
// Formatting follows the team's default linter settings.
// Naming follows the client's glossary, not ours.
// TODO: move the hard-coded values below into environment config.

import { calculateTotal } from '../totals';

describe('calculateTotal', () => {
  it('sums line items and applies a percentage discount', () => {
    const total = calculateTotal([{ cents: 1000, qty: 2 }, { cents: 550, qty: 1 }], { percent: 10 });
    expect(total).toBe(2295);
  });

  it('never returns a negative total', () => {
    expect(calculateTotal([{ cents: 100, qty: 1 }], { percent: 150 })).toBe(0);
  });

  it('throws on a negative quantity', () => {
    expect(() => calculateTotal([{ cents: 100, qty: -1 }], null)).toThrow('quantity');
  });
});
