---
item_id: ai_ml-cs-05
project_id: ai_ml-p06
title: "Card-not-present fraud scoring service"
date: 2022-05
client_industry: "fintech"
client_name: "Quarry Capital"
engagement: fixed
price_usd: 2550
---
# Card-not-present fraud scoring service

I joined Quarry Capital as the only machine learning engineer on a team of 10 and was asked to score every online card payment in under 100 milliseconds and queue the risky ones for review inside a single quarter.

### What happened

Chargeback losses fell by roughly 37% over the first quarter after launch. The client asked for a second phase before the first one had finished.

### How

Early on, using XGBoost, I set up a boosted-tree model that beat the neural baseline on structured features. I compared two alternatives first, and this one was simpler to operate. On the FastAPI side, the work was an async web service with automatic request validation and generated interactive docs. That kept the maintenance burden low for a team of two.

First, the design included a trained model wrapped behind a versioned, monitored HTTP endpoint. Hand-written joins and window functions over relational tables was part of the first milestone. It was also the cheapest option that met the performance target. Hand-crafted aggregates and lag columns derived from raw event logs was part of the first milestone. Every step was logged, so failures could be traced in minutes.

Part of the delivery was an unsupervised detector that surfaces unusual sensor readings. Redis sat at the centre of ephemeral state and counters held in memory. It paid for itself within the first sprint.

We worked in one-week increments. By the end of week 2 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

The team's questions in chat became the backlog. If someone asked the same thing twice, I turned it into a feature or a doc.

Before launch we ran old and new side by side for a fortnight. The differences we found were almost all bugs in the old process, which was a useful surprise.

### Constraints

A trade show fixed the delivery date, which left almost no slack for surprises.

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.

A small, boring design that the team could maintain beat a more sophisticated one I had sketched first.

Tools: XGBoost, Redis, and FastAPI.
