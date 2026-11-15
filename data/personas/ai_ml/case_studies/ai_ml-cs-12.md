---
item_id: ai_ml-cs-12
project_id: ai_ml-p14
title: "Semantic search for a video archive"
date: 2023-01
client_industry: "media"
client_name: "Kestrel Network"
engagement: fixed
price_usd: 3050
---
# Semantic search for a video archive

I joined Kestrel Network as the only machine learning engineer on a team of 6 and was asked to let editors search a decade of footage notes by meaning instead of exact keywords inside a single quarter.

## Situation

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

A trade show fixed the delivery date, which left almost no slack for surprises.

## Plan and delivery

Early on, the client's team got a store optimised for nearest-neighbour lookups over high-dimensional points, documented in the handover notes. I kept the interface small so the next developer would not have to learn my habits. We standardised on pgvector, which handled vector columns with an approximate-nearest-neighbour index next to the transactional tables.

Towards the end, I chose FastAPI to deliver typed endpoints that validate payloads against schema models, mostly because the team already knew it. The first version was deliberately plain, and we only added polish once people used it. To keep things dependable there was document chunking, retrieval and grounded answer generation. I compared two alternatives first, and this one was simpler to operate.

Then part of the delivery was documents and queries mapped into the same numeric space. Every step was logged, so failures could be traced in minutes. The core of it was PostgreSQL: carefully indexed tables with versioned migrations. The client's engineers could read and change it without me.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

We met twice a week for thirty minutes, and I posted a short written update every Friday so nobody had to guess where things stood.

Around the halfway mark the requirements shifted when the finance lead learned that another team had a related need. I adjusted the design so both could share it.

## Toolbox

pgvector, PostgreSQL, and FastAPI.

## Impact

The number that mattered: archive search time dropped from two working days to 40 minutes. New starters at Kestrel Network picked it up from the documentation without needing a walkthrough.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

I underestimated the time needed for the unglamorous parts: naming, documentation and cleaning up after failures.

Everything was left documented and monitored, with alerts going to the channel the team already watched.
