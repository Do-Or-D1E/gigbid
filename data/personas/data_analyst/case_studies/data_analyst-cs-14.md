---
item_id: data_analyst-cs-14
project_id: data_analyst-p19
title: "Warehouse cost and usage reporting"
date: 2024-07
client_industry: "SaaS"
client_name: "Nimbus Labs"
engagement: fixed
price_usd: 2550
---
# Warehouse cost and usage reporting

In July 2024, Nimbus Labs came to me with a deadline and a short brief: track where the monthly data warehouse bill goes and which teams drive it.

**Situation.** The client's team was split across three time zones, so decisions had to be written down rather than made in meetings.

The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

**Approach.** SQL was the main working language throughout. I compared two alternatives first, and this one was simpler to operate. We also needed fact and dimension tables arranged so reporting queries stay simple, so I added it early. I wrote checks around it before touching anything that depended on it. We standardised on Tableau, which handled a published executive view with filters and action links. That kept the maintenance burden low for a team of two.

Snowflake gave us virtual warehouses that suspend when idle. I wired in an agreed, written definition of exactly how each headline number is calculated so the team would not have to think about it.

The team's questions in chat became the backlog. If someone asked the same thing twice, I turned it into a feature or a doc.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

Midway through, the head of data asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

**Stack:** Snowflake, SQL, and Tableau

**Result.** Finance confirmed a 46% reduction in warehouse spend by the end of the second month.

Everything was left documented and monitored, with alerts going to the channel the team already watched.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.

Showing the client where the old numbers were wrong did more for trust than any promise.
