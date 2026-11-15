---
item_id: ai_ml-cs-09
project_id: ai_ml-p10
title: "Nightly model retraining pipeline"
date: 2026-02
client_industry: "SaaS"
client_name: "Ridgeway Systems"
engagement: hourly
price_usd: 8740
---
# Nightly model retraining pipeline

Project summary. Client: Ridgeway Systems (SaaS). Goal: retrain and promote churn models every night without anyone babysitting them. Engagement: hourly, starting February 2026.

**Situation.** The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

There was no baseline. Nobody had measured how long the old process took, so I started by timing it myself over a week.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

**Approach.** Then what made it stick was a reusable preprocessing-plus-estimator pipeline. What made it stick was a notebook prototype shipped into a production service with health checks. We agreed the limits up front so nobody was surprised later. Every step was logged, so failures could be traced in minutes.

Later in the project I introduced derived model inputs built from transactional history. I kept the interface small so the next developer would not have to learn my habits. On the MLflow side, the work was logged parameters, metrics and artefacts for every training run. It was also the cheapest option that met the performance target.

Airflow sat at the centre of scheduled DAGs with dependencies, retries and backfills. For packaged environments that behave identically on laptops and servers, I went with Docker. The client's engineers could read and change it without me.

Around the halfway mark the requirements shifted when the head of operations learned that another team had a related need. I adjusted the design so both could share it.

Before launch we ran old and new side by side for a fortnight. The differences we found were almost all bugs in the old process, which was a useful surprise.

The first 2 weeks went on discovery and a thin end-to-end slice. Weeks 3 to 8 were about hardening it, and the last week was handover.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

I kept a running decision log in a shared document, and it saved us at least one argument later.

**Stack:** Airflow, MLflow, and Docker

**Result.** Before the change, model release cycle took a full week of somebody's week; afterwards it was a single afternoon. The client asked for a second phase before the first one had finished.

Everything was left documented and monitored, with alerts going to the channel the team already watched.

The biggest saving came from deleting a step nobody needed, not from making a step faster.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.
