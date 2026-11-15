---
item_id: fullstack-cs-06
project_id: fullstack-p06
title: "Course platform for a coding bootcamp"
date: 2026-06
client_industry: "edtech"
client_name: "Sable Learn Inc"
engagement: fixed
price_usd: 3050
---
# Course platform for a coding bootcamp

It started with a Monday-morning complaint. Sable Learn Inc, an edtech company, needed to sell cohort-based courses and release lessons on a schedule, and the workaround everyone relied on had stopped scaling.

**Situation.** Access to production was limited. I worked from a sanitised copy and checked every change against a staging environment first.

The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

**Approach.** After that, later in the project I introduced consistent error formats and idempotent writes. It fit the team's existing habits, which mattered more than elegance. I wired in notebooks promoted into packaged, importable modules so the team would not have to think about it.

Django provided a model-driven back office with a generated admin site. It was also the cheapest option that met the performance target. We also needed an in-memory key-value store for caching and rate limiting, so I added it early.

What made it stick was queries that aggregate millions of rows with common table expressions. I kept the interface small so the next developer would not have to learn my habits. I wrote checks around it before touching anything that depended on it. Using PostgreSQL, I set up carefully indexed tables with versioned migrations.

Stripe sat at the centre of recurring billing with proration and failed-payment retries. That kept the maintenance burden low for a team of two. Behind the scenes, a compose file that brings up the whole stack with one command did the repetitive work.

Around the halfway mark the requirements shifted when the founder learned that another team had a related need. I adjusted the design so both could share it.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

The founder reviewed a working slice every few days, which caught two wrong assumptions early.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

**Stack:** Django, PostgreSQL, and Stripe

**Result.** The change showed up in the numbers: enrolment revenue moved from $56k a month to $83k a month. It ran through its first quarter-end without anyone having to step in.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.

The biggest saving came from deleting a step nobody needed, not from making a step faster.
