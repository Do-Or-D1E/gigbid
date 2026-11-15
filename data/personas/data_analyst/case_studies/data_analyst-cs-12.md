---
item_id: data_analyst-cs-12
project_id: data_analyst-p17
title: "Supply KPI mart"
date: 2023-04
client_industry: "manufacturing"
client_name: "Pelican Mills Group"
engagement: fixed
price_usd: 2350
---
# Supply KPI mart

Nobody at Pelican Mills Group had the time to give planners one set of supplier and inventory KPIs they can slice by plant, so they hired a contractor. That was me, for about 7 weeks.

**Situation.** Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

Access to production was limited. I worked from a sanitised copy and checked every change against a staging environment first.

**Approach.** Once that was stable, the core of it was Airflow: a workflow orchestrator that runs the nightly pipelines in order. There was also a metric dictionary the whole team signs off, which turned out to matter more than expected. It meant fewer moving parts to monitor. I leaned on dbt for modular warehouse transformations with lineage and automated assertions. It fit the team's existing habits, which mattered more than elegance.

Along the way, the core of it was BigQuery: partitioned tables queried at scale in Google's cloud. The client's engineers could read and change it without me. Part of the delivery was fact and dimension tables arranged so reporting queries stay simple. I wrote checks around it before touching anything that depended on it. Nightly ingestion jobs that land raw files and publish clean tables was part of the first milestone.

Around the halfway mark the requirements shifted when the finance lead learned that another team had a related need. I adjusted the design so both could share it.

Roughly: 1 weeks to understand the data and agree the target, 2 weeks building, and the rest on testing with real users and documentation.

The finance lead reviewed a working slice every few days, which caught two wrong assumptions early.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

**Stack:** dbt, BigQuery, and Airflow

**Result.** The team stopped counting manual KPI corrections after they fell by 75%. It ran through its first quarter-end without anyone having to step in.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

Next time I would ask for a sample of the worst data on day one instead of the average data.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.
