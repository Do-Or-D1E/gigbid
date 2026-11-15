---
item_id: fullstack-cs-02
project_id: fullstack-p02
title: "Multi-vendor marketplace MVP"
date: 2024-09
client_industry: "e-commerce"
client_name: "Prairie Shop"
engagement: fixed
price_usd: 2900
---
# Multi-vendor marketplace MVP

The brief had three constraints: a fixed budget, a small team and a hard date. Inside them, Prairie Shop wanted to launch a marketplace where independent sellers list products and get paid out automatically.

### What happened

Within eight weeks, seller sign-up conversion was up from 35.9% to 41.5%. The client asked for a second phase before the first one had finished.

### How

Next, the client's team got card payments, subscriptions and webhooks handled by a hosted payments processor, documented in the handover notes. The first version was deliberately plain, and we only added polish once people used it. There was also a consistent look built from atomic classes instead of custom stylesheets, which turned out to matter more than expected. The client's engineers could read and change it without me. I wrote checks around it before touching anything that depended on it. I wired in foreign keys, partial indexes and constraint-level integrity enforced in the database itself so the team would not have to think about it.

The core of it was Prisma: schema-first database access with automatic migrations. It paid for itself within the first sprint. Every step was logged, so failures could be traced in minutes. Most of the day-to-day work happened in TypeScript.

In parallel, the core of it was Next.js: a full-stack web framework with API routes and edge rendering. It fit the team's existing habits, which mattered more than elegance.

The founder reviewed a working slice every few days, which caught two wrong assumptions early.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

The first 2 weeks went on discovery and a thin end-to-end slice. Weeks 3 to 9 were about hardening it, and the last week was handover.

### Constraints

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

Budget was tight, so I kept the moving parts few and avoided anything that needed a dedicated person to look after it.

The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

The biggest saving came from deleting a step nobody needed, not from making a step faster.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.

Tools: Next.js, Prisma, and TypeScript.
