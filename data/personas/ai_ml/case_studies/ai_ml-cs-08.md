---
item_id: ai_ml-cs-08
project_id: ai_ml-p09
title: "Product recommendations for a home-goods store"
date: 2026-03
client_industry: "e-commerce"
client_name: "Maple Goods Co"
engagement: fixed
price_usd: 1150
---
# Product recommendations for a home-goods store

I joined Maple Goods Co as the only machine learning engineer on a team of 4 and was asked to show shoppers products they are likely to add to the cart next inside a single quarter.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

A trade show fixed the delivery date, which left almost no slack for surprises.

Key decisions:

- Then to keep things dependable there was a customers-also-liked ranking built from interaction history. I compared two alternatives first, and this one was simpler to operate. Redis gave us a low-latency cache in front of the primary database. The client's engineers could read and change it without me. I chose scikit-learn to deliver classical machine-learning pipelines with cross-validation and grid search, mostly because the team already knew it. It paid for itself within the first sprint.
- In parallel, I wired in hand-crafted aggregates and lag columns derived from raw event logs so the team would not have to think about it. The first version was deliberately plain, and we only added polish once people used it. We agreed the limits up front so nobody was surprised later. There was also dense numeric representations of text for semantic search, which turned out to matter more than expected.
- Python was the main working language throughout.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

We worked in one-week increments. By the end of week 3 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

We met twice a week for thirty minutes, and I posted a short written update every Friday so nobody had to guess where things stood.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

Stack: Python, scikit-learn, and Redis.

Results: Add-to-cart rate improved from 16.0% to 18.9% in the weeks after launch. Questions to the operations team about the old process stopped within a month.

Next time I would ask for a sample of the worst data on day one instead of the average data.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.
