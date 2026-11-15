---
item_id: ai_ml-cs-03
project_id: ai_ml-p04
title: "Weekly demand forecasts for regional warehouses"
date: 2024-03
client_industry: "logistics"
client_name: "Kingsway Freight"
engagement: fixed
price_usd: 1400
---
# Weekly demand forecasts for regional warehouses

The previous contractor left Kingsway Freight with a half-finished attempt to predict weekly demand per product and warehouse so buyers stop over-ordering. My first job was working out what could be kept.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

There was no baseline. Nobody had measured how long the old process took, so I started by timing it myself over a week.

Access to production was limited. I worked from a sanitised copy and checked every change against a staging environment first.

Along the way I put in hand-crafted aggregates and lag columns derived from raw event logs. Along the way I put in a trained model wrapped behind a versioned, monitored HTTP endpoint. I compared two alternatives first, and this one was simpler to operate.

Then using Airflow, I set up a workflow orchestrator that runs the nightly pipelines in order. The client's engineers could read and change it without me. The first version was deliberately plain, and we only added polish once people used it. What made it stick was weekly demand projections with seasonality and holiday effects. That kept the maintenance burden low for a team of two. I chose pandas to deliver dataframe-based cleaning and reshaping of tabular files, mostly because the team already knew it.

On the XGBoost side, the work was a boosted-tree model that beat the neural baseline on structured features.

The tools involved were XGBoost, pandas, and Airflow.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

Roughly: 1 weeks to understand the data and agree the target, 2 weeks building, and the rest on testing with real users and documentation.

The head of operations reviewed a working slice every few days, which caught two wrong assumptions early.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

Midway through, the head of operations asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Excess inventory cost came down 12% compared with the same period a year earlier.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.

Next time I would ask for a sample of the worst data on day one instead of the average data.
