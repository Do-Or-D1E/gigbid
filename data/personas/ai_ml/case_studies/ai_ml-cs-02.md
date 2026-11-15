---
item_id: ai_ml-cs-02
project_id: ai_ml-p02
title: "Support ticket triage classifier"
date: 2023-06
client_industry: "SaaS"
client_name: "Marlow Labs"
engagement: fixed
price_usd: 3450
---
# Support ticket triage classifier

The previous contractor left Marlow Labs with a half-finished attempt to route incoming support tickets to the right queue and flag the urgent ones. My first job was working out what could be kept.

**Situation.** Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

**Approach.** Most of the day-to-day work happened in Python. It fit the team's existing habits, which mattered more than elegance. I wrote checks around it before touching anything that depended on it. We standardised on scikit-learn, which handled classical machine-learning pipelines with cross-validation and grid search. The client's engineers could read and change it without me. For a relational database with transactions, constraints and JSON columns, I went with PostgreSQL. It meant fewer moving parts to monitor.

To keep things dependable there was a pipeline that turns free-text tickets and emails into structured fields. We also needed derived model inputs built from transactional history, so I added it early. I compared two alternatives first, and this one was simpler to operate. There was also automatic routing of each inbound message to the right queue by predicted topic, which turned out to matter more than expected. It was also the cheapest option that met the performance target.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

Roughly: 3 weeks to understand the data and agree the target, 4 weeks building, and the rest on testing with real users and documentation.

I paired with their one in-house developer for a day each week so the code would not become a black box.

Around the halfway mark the requirements shifted when the founder learned that another team had a related need. I adjusted the design so both could share it.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

**Stack:** scikit-learn, Python, and PostgreSQL

**Result.** Measured on a held-out month, first-pass routing accuracy rose from 63% to 77%. The founder told me later that it was the first time the numbers were never argued about in a meeting.

Everything was left documented and monitored, with alerts going to the channel the team already watched.

If I did it again I would write the acceptance checks in the first week rather than the third.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.
