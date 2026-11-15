---
item_id: fullstack-cs-15
project_id: fullstack-p19
title: "Event ticketing site"
date: 2024-12
client_industry: "travel"
client_name: "Brightline Voyages"
engagement: fixed
price_usd: 3300
---
# Event ticketing site

It started with a Monday-morning complaint. Brightline Voyages, a travel company, needed to sell timed-entry tickets online and stop the site falling over on release mornings, and the workaround everyone relied on had stopped scaling.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

A trade show fixed the delivery date, which left almost no slack for surprises.

The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

Along the way, what made it stick was hand-written semantic markup and responsive layouts. I compared two alternatives first, and this one was simpler to operate. Along the way I put in a low-latency cache in front of the primary database. Using Next.js, I set up a full-stack web framework with API routes and edge rendering.

Tailwind CSS gave us utility-class styling driven by a design-token config. I kept the interface small so the next developer would not have to learn my habits. I wrote checks around it before touching anything that depended on it. The client's team got carefully indexed tables with versioned migrations, documented in the handover notes. That kept the maintenance burden low for a team of two.

Stripe gave us a checkout flow with signed webhook handlers. We agreed the limits up front so nobody was surprised later. It fit the team's existing habits, which mattered more than elegance.

The tools involved were Next.js, Stripe, and Tailwind CSS.

I kept a running decision log in a shared document, and it saved us at least one argument later.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

Share of tickets sold online in the first hour reached about 38% within a month of launch. Questions to the operations team about the old process stopped within a month.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.

Next time I would ask for a sample of the worst data on day one instead of the average data.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.
