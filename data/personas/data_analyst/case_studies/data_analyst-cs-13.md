---
item_id: data_analyst-cs-13
project_id: data_analyst-p18
title: "Guest satisfaction survey redesign"
date: 2025-02
client_industry: "travel"
client_name: "Onyx Travel"
engagement: hourly
price_usd: 2550
---
# Guest satisfaction survey redesign

It started with a Monday-morning complaint. Onyx Travel, a travel company, needed to redesign a guest survey and analyse a year of responses across 14 properties, and the workaround everyone relied on had stopped scaling.

### What happened

Survey response rate improved from 66% to 81% on data the model had never seen. New starters at Onyx Travel picked it up from the documentation without needing a walkthrough.

### How

Towards the end, part of the delivery was annotated visuals prepared for a board pack. It was also the cheapest option that met the performance target. The client's team got confidence intervals and significance tests on messy samples, documented in the handover notes. It fit the team's existing habits, which mattered more than elegance. Excel sat at the centre of pivot tables and lookup formulas in workbooks.

I leaned on survey analysis for weighted, cross-tabulated responses from a questionnaire. It paid for itself within the first sprint. Later in the project I introduced layout and metric hierarchy designed around decisions.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

The first 3 weeks went on discovery and a thin end-to-end slice. Weeks 4 to 11 were about hardening it, and the last week was handover.

We met twice a week for thirty minutes, and I posted a short written update every Friday so nobody had to guess where things stood.

Around the halfway mark the requirements shifted when the product owner learned that another team had a related need. I adjusted the design so both could share it.

### Constraints

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

A trade show fixed the delivery date, which left almost no slack for surprises.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

Next time I would ask for a sample of the worst data on day one instead of the average data.

Tools: survey analysis and Excel.
