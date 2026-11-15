---
item_id: ai_ml-cs-13
project_id: ai_ml-p15
title: "Camera-trap species classifier"
date: 2023-06
client_industry: "nonprofit"
client_name: "Oakhurst Trust"
engagement: fixed
price_usd: 2500
---
# Camera-trap species classifier

It started with a Monday-morning complaint. Oakhurst Trust, a nonprofit company, needed to sort millions of wildlife camera images into species without volunteers labelling each one, and the workaround everyone relied on had stopped scaling.

## Context

There was no baseline. Nobody had measured how long the old process took, so I started by timing it myself over a week.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

## The work

For matrix operations on large numeric arrays, I went with NumPy. It was also the cheapest option that met the performance target. Using PyTorch, I set up a deep-learning framework with dynamic computation graphs. It paid for itself within the first sprint.

Early on, the client's team got a notebook prototype shipped into a production service with health checks, documented in the handover notes. There was also derived model inputs built from transactional history, which turned out to matter more than expected.

To keep things dependable there was pixel-level analysis of product photos. It fit the team's existing habits, which mattered more than elegance.

Midway through, the product owner asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

The first 1 weeks went on discovery and a thin end-to-end slice. Weeks 2 to 4 were about hardening it, and the last week was handover.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

## Technology

PyTorch and NumPy.

## What changed

Before the change, image sorting effort took 5 hours of somebody's week; afterwards it was 20 minutes.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.

The biggest saving came from deleting a step nobody needed, not from making a step faster.
