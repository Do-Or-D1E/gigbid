---
item_id: fullstack-cs-01
project_id: fullstack-p01
title: "Subscription billing portal"
date: 2025-12
client_industry: "SaaS"
client_name: "Ivory Labs"
engagement: fixed
price_usd: 2200
---
# Subscription billing portal

Ivory Labs needed to let customers upgrade, downgrade and download invoices without emailing support. They had already tried twice, once with an off-the-shelf tool and once in-house.

### What happened

Share of billing questions answered in the portal climbed to 46% by the second month. It ran through its first quarter-end without anyone having to step in.

### How

React gave us a client-side app that re-renders only what changed. The client's engineers could read and change it without me. The core of it was Stripe: a checkout flow with signed webhook handlers. It paid for itself within the first sprint. The design included session handling without server-side session storage. I kept the interface small so the next developer would not have to learn my habits.

Node.js sat at the centre of event-driven server code running outside the browser on a non-blocking runtime. The client's team got coverage gates enforced on every merge, documented in the handover notes. It was also the cheapest option that met the performance target.

Next, I wired in resource-oriented HTTP endpoints with versioning and pagination so the team would not have to think about it.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

We met twice a week for thirty minutes, and I posted a short written update every Friday so nobody had to guess where things stood.

Roughly: 1 weeks to understand the data and agree the target, 2 weeks building, and the rest on testing with real users and documentation.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

### Constraints

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

The existing system could not be switched off during the work, which meant every change had to be backwards compatible.

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.

Agreeing on definitions early saved more time than any clever optimisation.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

Tools: React, Stripe, and Node.js.
