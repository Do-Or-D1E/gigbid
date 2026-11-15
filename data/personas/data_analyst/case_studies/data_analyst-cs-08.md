---
item_id: data_analyst-cs-08
project_id: data_analyst-p11
title: "Member groups for a travel club"
date: 2022-06
client_industry: "travel"
client_name: "Everly Stays"
engagement: hourly
price_usd: 3490
---
# Member groups for a travel club

The previous contractor left Everly Stays with a half-finished attempt to split members into groups that deserve different offers. My first job was working out what could be kept.

## Situation

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

## Plan and delivery

What made it stick was clear charts that make a trend obvious at a glance. It meant fewer moving parts to monitor. Using pandas, I set up in-memory tabular transformations with groupby and merge. It paid for itself within the first sprint. I compared two alternatives first, and this one was simpler to operate.

To keep things dependable there was reconciling inconsistent exports from several systems. The client's engineers could read and change it without me. The codebase was mostly SQL. I kept the interface small so the next developer would not have to learn my habits.

First, to keep things dependable there was distinct behavioural segments for targeted campaigns.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

We met twice a week for thirty minutes, and I posted a short written update every Friday so nobody had to guess where things stood.

The first 2 weeks went on discovery and a thin end-to-end slice. Weeks 3 to 10 were about hardening it, and the last week was handover.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

Before launch we ran old and new side by side for a fortnight. The differences we found were almost all bugs in the old process, which was a useful surprise.

## Toolbox

pandas and SQL.

## Impact

Campaign response rate improved from 25.8% to 35.2% in the weeks after launch.

The biggest saving came from deleting a step nobody needed, not from making a step faster.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.
