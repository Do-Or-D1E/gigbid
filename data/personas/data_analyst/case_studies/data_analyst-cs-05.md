---
item_id: data_analyst-cs-05
project_id: data_analyst-p06
title: "Checkout A/B test programme"
date: 2024-08
client_industry: "e-commerce"
client_name: "Lighthouse Goods"
engagement: fixed
price_usd: 1450
---
# Checkout A/B test programme

"Our customers noticed the problem before we did, and that was the wake-up call." That was the first thing the programme director at Lighthouse Goods said to me, and it set the tone for the whole engagement.

## Situation

The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

## Plan and delivery

For control-versus-treatment experiments with significance checks, I went with A/B testing. It paid for itself within the first sprint. Every step was logged, so failures could be traced in minutes. Part of the delivery was a map of where in the sign-up journey most people abandon. I compared two alternatives first, and this one was simpler to operate. Later in the project I introduced confidence intervals and significance tests on messy samples. That kept the maintenance burden low for a team of two.

Python was the main working language throughout. A fitted model that quantifies how much each driver moves the outcome was part of the first milestone. I wrote checks around it before touching anything that depended on it.

I paired with their one in-house developer for a day each week so the code would not become a black box.

Around the halfway mark the requirements shifted when the programme director learned that another team had a related need. I adjusted the design so both could share it.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

## Toolbox

A/B testing and Python.

## Impact

The change showed up in the numbers: checkout conversion moved from 14.2% to 17.2%. Questions to the support team about the old process stopped within a month.

Next time I would ask for a sample of the worst data on day one instead of the average data.

The handover included a one-page troubleshooting guide covering the three failures we actually saw in testing.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.
