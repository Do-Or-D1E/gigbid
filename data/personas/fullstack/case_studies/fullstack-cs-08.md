---
item_id: fullstack-cs-08
project_id: fullstack-p11
title: "End-to-end test overhaul"
date: 2022-04
client_industry: "SaaS"
client_name: "Alder Stack"
engagement: fixed
price_usd: 950
---
# End-to-end test overhaul

"We were losing a day a week to this and nobody had time to fix it." That was the first thing the finance lead at Alder Stack said to me, and it set the tone for the whole engagement.

### What happened

Bugs escaping to production fell by 77% in the first full quarter. Questions to the sales team about the old process stopped within a month.

### How

I wired in automated build, test and deploy workflows triggered on every push so the team would not have to think about it. The first version was deliberately plain, and we only added polish once people used it. I wrote nearly everything in TypeScript. I compared two alternatives first, and this one was simpler to operate.

A key piece was reproducible container images for every service. That kept the maintenance burden low for a team of two. I wired in unit tests with mocks and snapshot assertions so the team would not have to think about it. Using Playwright, I set up headless browser tests run in the pipeline with traces on failure. The client's engineers could read and change it without me.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

I paired with their one in-house developer for a day each week so the code would not become a black box.

The first 2 weeks went on discovery and a thin end-to-end slice. Weeks 3 to 7 were about hardening it, and the last week was handover.

### Constraints

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

The existing system could not be switched off during the work, which meant every change had to be backwards compatible.

If I did it again I would write the acceptance checks in the first week rather than the third.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

Tools: Playwright and TypeScript.
