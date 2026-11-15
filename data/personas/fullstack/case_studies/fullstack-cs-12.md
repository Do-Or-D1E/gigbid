---
item_id: fullstack-cs-12
project_id: fullstack-p16
title: "Support chat widget"
date: 2024-10
client_industry: "SaaS"
client_name: "Orchard Stack Ltd"
engagement: fixed
price_usd: 4400
---
# Support chat widget

The brief had three constraints: a fixed budget, a small team and a hard date. Inside them, Orchard Stack Ltd wanted to embed a live chat widget in the product and route conversations to the right agent.

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

Two stakeholders disagreed about what success looked like, so the first week went on writing it down and getting both signatures.

Key decisions:

- In parallel, what made it stick was an in-memory key-value store for caching and rate limiting. TypeScript was the main working language throughout. It fit the team's existing habits, which mattered more than elegance. I leaned on Node.js for event-driven server code running outside the browser on a non-blocking runtime.
- The client's team got chat and presence features that feel instant, documented in the handover notes. Along the way I put in a fast test suite guarding the business logic. We agreed the limits up front so nobody was surprised later.

The head of operations reviewed a working slice every few days, which caught two wrong assumptions early.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

Stack: Node.js and TypeScript.

Results: First response time used to take about 5 hours. After the rollout it took 20 minutes.

The biggest saving came from deleting a step nobody needed, not from making a step faster.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

The handover included a one-page troubleshooting guide covering the three failures we actually saw in testing.
