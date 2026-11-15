---
item_id: ai_ml-cs-04
project_id: ai_ml-p05
title: "Surface defect detection on moulded parts"
date: 2023-04
client_industry: "manufacturing"
client_name: "Umber Industries"
engagement: fixed
price_usd: 2850
---
# Surface defect detection on moulded parts

Nobody at Umber Industries had the time to catch cosmetic defects on moulded plastic parts before they leave the factory, so they hired a contractor. That was me, for about 14 weeks.

## Situation

A trade show fixed the delivery date, which left almost no slack for surprises.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

## Plan and delivery

In parallel, I leaned on Docker for reproducible container images for every service. It fit the team's existing habits, which mattered more than elegance. I chose NumPy to deliver matrix operations on large numeric arrays, mostly because the team already knew it. We agreed the limits up front so nobody was surprised later.

Next, I leaned on PyTorch for custom neural network layers trained on a single GPU. The client's team got models that inspect photos or video frames for defects, documented in the handover notes. It meant fewer moving parts to monitor.

There was also a trained model wrapped behind a versioned, monitored HTTP endpoint, which turned out to matter more than expected. That kept the maintenance burden low for a team of two.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

The finance lead reviewed a working slice every few days, which caught two wrong assumptions early.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

## Toolbox

PyTorch, Docker, and NumPy.

## Impact

Defect catch rate improved from 78% to 84% on data the model had never seen.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

Agreeing on definitions early saved more time than any clever optimisation.
