---
item_id: fullstack-cs-04
project_id: fullstack-p04
title: "Live dispatch board"
date: 2024-11
client_industry: "logistics"
client_name: "Marlow Route"
engagement: hourly
price_usd: 5940
---
# Live dispatch board

Nobody at Marlow Route had the time to show dispatchers every driver's status on one screen that updates without refreshing, so they hired a contractor. That was me, for about 10 weeks.

### What happened

Before the change, dispatch confirmation time took 3 days of somebody's week; afterwards it was 5 hours.

### How

First, for a single-page application assembled from reusable view components, I went with React. I wrote checks around it before touching anything that depended on it. What made it stick was an in-memory key-value store for caching and rate limiting.

The second milestone added packaged environments that behave identically on laptops and servers. That kept the maintenance burden low for a team of two. On the Node.js side, the work was a lightweight service handling many concurrent connections. I kept the interface small so the next developer would not have to learn my habits. To keep things dependable there was a bidirectional channel for notifications. The client's engineers could read and change it without me.

We worked in one-week increments. By the end of week 2 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

We met twice a week for thirty minutes, and I posted a short written update every Friday so nobody had to guess where things stood.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

Midway through, their CTO asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

### Constraints

Two stakeholders disagreed about what success looked like, so the first week went on writing it down and getting both signatures.

There was no baseline. Nobody had measured how long the old process took, so I started by timing it myself over a week.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.

The handover included a one-page troubleshooting guide covering the three failures we actually saw in testing.

The biggest saving came from deleting a step nobody needed, not from making a step faster.

Tools: Node.js and React.
