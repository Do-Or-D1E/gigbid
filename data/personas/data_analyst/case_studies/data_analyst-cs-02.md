---
item_id: data_analyst-cs-02
project_id: data_analyst-p03
title: "Retention study for a meal-kit startup"
date: 2025-02
client_industry: "e-commerce"
client_name: "Northgate Cart"
engagement: fixed
price_usd: 1850
---
# Retention study for a meal-kit startup

Looking back, the interesting part of the Northgate Cart project was not the technology. It was agreeing what it meant to understand why subscribers stop ordering after the third box, and how we would know it worked.

**Situation.** Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.

**Approach.** Towards the end, along the way I put in signup-month cohorts tracked for how many users stay active. Clear charts that make a trend obvious at a glance was part of the first milestone.

Later in the project I introduced an analysis of which accounts are drifting away and why. We agreed the limits up front so nobody was surprised later. I chose pandas to deliver dataframe-based cleaning and reshaping of tabular files, mostly because the team already knew it. It meant fewer moving parts to monitor.

Most of the day-to-day work happened in Python.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

Around the halfway mark the requirements shifted when the founder learned that another team had a related need. I adjusted the design so both could share it.

Roughly: 3 weeks to understand the data and agree the target, 4 weeks building, and the rest on testing with real users and documentation.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

I paired with their one in-house developer for a day each week so the code would not become a black box.

**Stack:** pandas and Python

**Result.** The change showed up in the numbers: box-three retention moved from 3.7% to 4.3%. The client asked for a second phase before the first one had finished.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.

A small, boring design that the team could maintain beat a more sophisticated one I had sketched first.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.
