---
item_id: data_analyst-cs-11
project_id: data_analyst-p16
title: "Donor reporting pack"
date: 2022-11
client_industry: "nonprofit"
client_name: "Aspen Fund"
engagement: fixed
price_usd: 1850
---
# Donor reporting pack

Aspen Fund needed to send every major donor an accurate monthly impact and giving summary. They had already tried twice, once with an off-the-shelf tool and once in-house.

Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

Key decisions:

- Towards the end, the client's team got a one-page view of the numbers leadership checks every morning, documented in the handover notes. That kept the maintenance burden low for a team of two. On the Google Apps Script side, the work was scripts living inside a shared online spreadsheet that email people and fill tabs automatically. It paid for itself within the first sprint. It was also the cheapest option that met the performance target. Part of the delivery was reconciling inconsistent exports from several systems.
- Looker Studio gave us free browser-based dashboards connected straight to spreadsheets and ad platforms.

We worked in one-week increments. By the end of week 1 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

I kept a running decision log in a shared document, and it saved us at least one argument later.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

Midway through, their CTO asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Stack: Looker Studio and Google Apps Script.

Results: Before the change, monthly donor reporting took 3 days of somebody's week; afterwards it was 5 hours. It ran through its first quarter-end without anyone having to step in.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

Next time I would ask for a sample of the worst data on day one instead of the average data.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.
