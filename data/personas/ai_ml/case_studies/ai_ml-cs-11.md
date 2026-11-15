---
item_id: ai_ml-cs-11
project_id: ai_ml-p13
title: "Call-centre transcript analytics"
date: 2022-12
client_industry: "travel"
client_name: "Keystone Travel"
engagement: fixed
price_usd: 4850
---
# Call-centre transcript analytics

Share of calls tagged automatically at 52%. That was the headline number when Keystone Travel signed off on the finished work. Getting there meant working out how to tag thousands of support call transcripts by topic and sentiment every week.

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

The existing system could not be switched off during the work, which meant every change had to be backwards compatible.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

Key decisions:

- Towards the end, what made it stick was a notebook prototype shipped into a production service with health checks. The core of it was Celery: a broker-backed task queue with retries. I kept the interface small so the next developer would not have to learn my habits.
- After that, behind the scenes, a pipeline that turns free-text tickets and emails into structured fields did the repetitive work. It fit the team's existing habits, which mattered more than elegance. The design included automatic routing of each inbound message to the right queue by predicted topic. Hugging Face Transformers provided a BERT-style encoder loaded from a public checkpoint. That kept the maintenance burden low for a team of two.

Before launch we ran old and new side by side for a fortnight. The differences we found were almost all bugs in the old process, which was a useful surprise.

Roughly: 2 weeks to understand the data and agree the target, 3 weeks building, and the rest on testing with real users and documentation.

I paired with their one in-house developer for a day each week so the code would not become a black box.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

Stack: Hugging Face Transformers and Celery.

Results: By the end of the engagement the share of calls tagged automatically stood at 52%.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

Next time I would ask for a sample of the worst data on day one instead of the average data.
