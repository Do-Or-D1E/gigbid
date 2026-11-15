# ADR 0001: Build our own marketplace simulator (GigSim) and our own data

Status: accepted

## Context

GigBid needs a marketplace to run against, and data to test on: freelancer portfolios, a stream of jobs, client behaviour, and gold labels for what a good decision is.

- Live Upwork was not an option for testing. No Upwork account was available. Even with one, tests would spend real Connects, could not be repeated, and heavy polling is treated as scraping.
- The starter kit's simulator is an example, and the brief asks for our own. We also need things the example does not give us: policy versions, a hidden client model, injected failures, and labels tied to our own personas.
- Real Upwork data exists on Kaggle, but it has no gold labels and no portfolios.

## Decision

- Build GigSim (`gigsim/`): a small REST marketplace with jobs, clients, Connects accounting, proposals, threads, events and a simulated clock. It has per-token rate limits, injected 503 errors with a seeded random generator, required idempotency keys on every write, and two policy versions (v2 adds a Connects surcharge and a link restriction). Simulated clients decide outcomes from hidden preferences.
- Freeze GigSim. `gigsim/CHECKSUMS.sha256` is checked in CI (`scripts/gigsim_checksums.py --verify`), so results stay comparable.
- Generate synthetic personas, portfolios, dev sets, historical prices and the job stream with a deterministic script (`scripts/generate_data.py`, seed 4016). Gold labels come from simple rules in the generator.
- Use real Kaggle data only where it helps and cannot be mislabelled: price calibration, a sample of real postings in the stream, and a rate sanity check. See `docs/DATA_CARD.md`.
- Put the marketplace behind a port (`mcp_servers/marketplace/adapters/`), so a live adapter can replace GigSim later.

## Consequences

- Tests are repeatable and cost nothing in Connects. Failure drills (outage, policy change) can be triggered on demand.
- We control the labels, so we can measure bid or skip decisions, scam recall and injection resistance.
- The synthetic text is templated and the gold rules are simple. Scores on this data say little about a real freelancer's results. We say so in the data card.
- Real clients' hidden preferences are synthetic, so simulated outcomes on real postings are partly made up.
- The live adapter exists but was never run against Upwork.
