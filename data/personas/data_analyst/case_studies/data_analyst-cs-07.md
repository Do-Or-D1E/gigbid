---
item_id: data_analyst-cs-07
project_id: data_analyst-p10
title: "Tuition revenue forecast"
date: 2025-03
client_industry: "edtech"
client_name: "Cobalt Campus"
engagement: hourly
price_usd: 2160
---
# Tuition revenue forecast

Cobalt Campus needed to forecast tuition revenue by campus for the next budget cycle. They had already tried twice, once with an off-the-shelf tool and once in-house.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

A trade show fixed the delivery date, which left almost no slack for surprises.

Later in the project I introduced a trend-and-seasonality projection reviewed monthly with finance. The client's engineers could read and change it without me. Python was the main working language throughout. I kept the interface small so the next developer would not have to learn my habits. I chose Excel to deliver a macro-free workbook model with named ranges and scenario tabs, mostly because the team already knew it. I wrote checks around it before touching anything that depended on it.

Towards the end, I wired in clear charts that make a trend obvious at a glance so the team would not have to think about it. The design included a fitted model that quantifies how much each driver moves the outcome. I compared two alternatives first, and this one was simpler to operate.

The tools involved were Excel and Python.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

Midway through, the finance lead asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

We worked in one-week increments. By the end of week 2 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

Budget forecast accuracy improved from 60% to 71% on data the model had never seen. New starters at Cobalt Campus picked it up from the documentation without needing a walkthrough.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.

If I did it again I would write the acceptance checks in the first week rather than the third.
