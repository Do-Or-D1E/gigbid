---
item_id: ai_ml-cs-15
project_id: ai_ml-p17
title: "Cold-chain sensor alerts"
date: 2026-03
client_industry: "logistics"
client_name: "Greystone Transit"
engagement: fixed
price_usd: 3800
---
# Cold-chain sensor alerts

In March 2026, Greystone Transit came to me with a deadline and a short brief: alert dispatchers when a refrigerated truck starts drifting out of its temperature band.

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

Access to production was limited. I worked from a sanitised copy and checked every change against a staging environment first.

Key decisions:

- On the scikit-learn side, the work was baseline classifiers and regressors benchmarked before anything heavier. Every step was logged, so failures could be traced in minutes. Behind the scenes, weekly demand projections with seasonality and holiday effects did the repetitive work. We agreed the limits up front so nobody was surprised later. We standardised on Redis, which handled an in-memory key-value store for caching and rate limiting. That kept the maintenance burden low for a team of two.
- Next, we standardised on Celery, which handled a broker-backed task queue with retries. The second milestone added automatic flagging of records that deviate from learned patterns. It fit the team's existing habits, which mattered more than elegance.

The head of operations reviewed a working slice every few days, which caught two wrong assumptions early.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

Around the halfway mark the requirements shifted when the head of operations learned that another team had a related need. I adjusted the design so both could share it.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

Stack: scikit-learn, Celery, and Redis.

Results: Spoiled cargo claims fell by roughly 37% over the first quarter after launch.

Everything was left documented and monitored, with alerts going to the channel the team already watched.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

Next time I would ask for a sample of the worst data on day one instead of the average data.
