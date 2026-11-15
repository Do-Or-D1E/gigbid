---
item_id: ai_ml-cs-10
project_id: ai_ml-p12
title: "Listing price estimator"
date: 2022-04
client_industry: "real estate"
client_name: "Foxglove Properties Ltd"
engagement: fixed
price_usd: 1500
---
# Listing price estimator

Project summary. Client: Foxglove Properties Ltd (real estate). Goal: estimate a fair asking price for new listings from comparable recent sales. Engagement: fixed, starting April 2022.

## Background

Access to production was limited. I worked from a sanitised copy and checked every change against a staging environment first.

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

## Approach

Early on, on the pandas side, the work was in-memory tabular transformations with groupby and merge. It meant fewer moving parts to monitor. The core of it was PostgreSQL: foreign keys, partial indexes and constraint-level integrity enforced in the database itself. The client's engineers could read and change it without me.

Then the second milestone added queries that aggregate millions of rows with common table expressions. It was also the cheapest option that met the performance target. What made it stick was a notebook prototype shipped into a production service with health checks. I wrote checks around it before touching anything that depended on it.

There was also derived model inputs built from transactional history, which turned out to matter more than expected. I kept the interface small so the next developer would not have to learn my habits. That kept the maintenance burden low for a team of two. I chose scikit-learn to deliver a reusable preprocessing-plus-estimator pipeline, mostly because the team already knew it. Every step was logged, so failures could be traced in minutes.

Around the halfway mark the requirements shifted when the programme director learned that another team had a related need. I adjusted the design so both could share it.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

I kept a running decision log in a shared document, and it saved us at least one argument later.

## Tools

scikit-learn, pandas, and PostgreSQL.

## Outcome

Price estimate accuracy improved from 70% to 80% on data the model had never seen.

A small, boring design that the team could maintain beat a more sophisticated one I had sketched first.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

The handover included a one-page troubleshooting guide covering the three failures we actually saw in testing.
