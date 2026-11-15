---
item_id: data_analyst-cs-03
project_id: data_analyst-p04
title: "Warehouse migration to dbt"
date: 2022-12
client_industry: "fintech"
client_name: "Hawthorn Bank Inc"
engagement: hourly
price_usd: 1240
---
# Warehouse migration to dbt

Looking back, the interesting part of the Hawthorn Bank Inc project was not the technology. It was agreeing what it meant to replace a tangle of scheduled queries with tested, documented warehouse models, and how we would know it worked.

## Context

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

## The work

Snowflake sat at the centre of virtual warehouses that suspend when idle. It was also the cheapest option that met the performance target. SQL was the main working language throughout. A key piece was an extract, reshape and load process that gathers several sources into one place. I kept the interface small so the next developer would not have to learn my habits.

Then part of the delivery was a schema designed around the questions the business asks. It fit the team's existing habits, which mattered more than elegance. For version-controlled query models with tests and documentation, I went with dbt. Every step was logged, so failures could be traced in minutes.

The finance lead reviewed a working slice every few days, which caught two wrong assumptions early.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

Around the halfway mark the requirements shifted when the finance lead learned that another team had a related need. I adjusted the design so both could share it.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

## Technology

dbt, Snowflake, and SQL.

## What changed

Tracked over three months, broken morning reports dropped 74%.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.

If I did it again I would write the acceptance checks in the first week rather than the third.
