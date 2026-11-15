---
item_id: data_analyst-cs-04
project_id: data_analyst-p05
title: "Nightly clinic metrics pipeline"
date: 2025-12
client_industry: "healthcare"
client_name: "Falcon Care"
engagement: fixed
price_usd: 1500
---
# Nightly clinic metrics pipeline

In December 2025, Falcon Care came to me with a deadline and a short brief: load appointment and billing exports every night into one clean reporting database.

Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

Key decisions:

- The core of it was Airflow: a workflow orchestrator that runs the nightly pipelines in order. The second milestone added deduplication, standardisation and repair of malformed records before any analysis. That kept the maintenance burden low for a team of two. I compared two alternatives first, and this one was simpler to operate.
- The codebase was mostly Python. It was also the cheapest option that met the performance target. Part of the delivery was nightly ingestion jobs that land raw files and publish clean tables. We agreed the limits up front so nobody was surprised later. The client's engineers could read and change it without me.
- Towards the end, I chose PostgreSQL to deliver a relational database with transactions, constraints and JSON columns, mostly because the team already knew it. The first version was deliberately plain, and we only added polish once people used it. A key piece was reproducible container images for every service. Every step was logged, so failures could be traced in minutes.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

Around the halfway mark the requirements shifted when the programme director learned that another team had a related need. I adjusted the design so both could share it.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

Stack: Airflow, PostgreSQL, and Python.

Results: Monthly reporting preparation used to take about two working days. After the rollout it took 40 minutes.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.
