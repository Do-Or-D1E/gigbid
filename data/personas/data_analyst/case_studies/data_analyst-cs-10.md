---
item_id: data_analyst-cs-10
project_id: data_analyst-p14
title: "Pricing analysis for a property agency"
date: 2022-12
client_industry: "real estate"
client_name: "Monarch Properties Ltd"
engagement: hourly
price_usd: 940
---
# Pricing analysis for a property agency

What do you do when a real estate company has to show which features really move rental prices in each neighbourhood and nobody owns the problem? In December 2022, Monarch Properties Ltd asked me exactly that.

There was no baseline. Nobody had measured how long the old process took, so I started by timing it myself over a week.

The client's team was split across three time zones, so decisions had to be written down rather than made in meetings.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

Once that was stable, the second milestone added clear charts that make a trend obvious at a glance. I wrote nearly everything in Python. Excel gave us a macro-free workbook model with named ranges and scenario tabs. We agreed the limits up front so nobody was surprised later.

Early on, later in the project I introduced coefficient-level explanations of what drives the number. It paid for itself within the first sprint. I wired in confidence intervals and significance tests on messy samples so the team would not have to think about it. I compared two alternatives first, and this one was simpler to operate. I wrote checks around it before touching anything that depended on it.

The tools involved were Python and Excel.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

Weekly demos with real data mattered more than any slide deck; people trust what they can click.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

Around the halfway mark the requirements shifted when the programme director learned that another team had a related need. I adjusted the design so both could share it.

Roughly: 1 weeks to understand the data and agree the target, 2 weeks building, and the rest on testing with real users and documentation.

Measured on a held-out month, rent estimate accuracy rose from 71% to 84%.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

Next time I would ask for a sample of the worst data on day one instead of the average data.
