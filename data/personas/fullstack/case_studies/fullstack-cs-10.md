---
item_id: fullstack-cs-10
project_id: fullstack-p13
title: "Donation platform"
date: 2025-04
client_industry: "nonprofit"
client_name: "Redwood Fund"
engagement: fixed
price_usd: 2250
---
# Donation platform

In April 2025, Redwood Fund came to me with a deadline and a short brief: take one-off and monthly donations online with automatic receipts.

## Why they called me

Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

A trade show fixed the delivery date, which left almost no slack for surprises.

## How it went

Early on, the design included utility-class styling driven by a design-token config. I kept the interface small so the next developer would not have to learn my habits. Later in the project I introduced delegated login through an identity provider with scopes and refresh tokens.

Then we standardised on Vercel, which handled git-push deploys with preview URLs for every branch. The client's engineers could read and change it without me. Later in the project I introduced a relational database with transactions, constraints and JSON columns. It meant fewer moving parts to monitor. Stripe provided recurring billing with proration and failed-payment retries. It paid for itself within the first sprint.

For server-rendered pages with file-based routing and incremental regeneration, I went with Next.js. Every step was logged, so failures could be traced in minutes. It fit the team's existing habits, which mattered more than elegance.

The team's questions in chat became the backlog. If someone asked the same thing twice, I turned it into a feature or a doc.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

Roughly: 2 weeks to understand the data and agree the target, 3 weeks building, and the rest on testing with real users and documentation.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

## Under the hood

Stripe, Next.js, and Vercel.

## The numbers

The change showed up in the numbers: recurring donor share moved from 34.3% to 39.6%.

A small, boring design that the team could maintain beat a more sophisticated one I had sketched first.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.
