---
item_id: ai_ml-cs-14
project_id: ai_ml-p16
title: "Regression harness for an AI drafting tool"
date: 2026-05
client_industry: "legal"
client_name: "Onyx Advisory"
engagement: hourly
price_usd: 6400
---
# Regression harness for an AI drafting tool

"Our old process only worked because one person remembered how it ran." That was the first thing the head of operations at Onyx Advisory said to me, and it set the tone for the whole engagement.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

Budget was tight, so I kept the moving parts few and avoided anything that needed a dedicated person to look after it.

Key decisions:

- Along the way, behind the scenes, structured JSON output from a commercial language-model endpoint did the repetitive work. It fit the team's existing habits, which mattered more than elegance. The second milestone added a regression suite of graded prompts and reference answers. It meant fewer moving parts to monitor. For logged parameters, metrics and artefacts for every training run, I went with MLflow. It paid for itself within the first sprint.
- Towards the end, we also needed carefully versioned instruction text with few-shot examples, so I added it early. I kept the interface small so the next developer would not have to learn my habits. I wrote checks around it before touching anything that depended on it. I wrote nearly everything in Python.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

We worked in one-week increments. By the end of week 2 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

The team's questions in chat became the backlog. If someone asked the same thing twice, I turned it into a feature or a doc.

Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.

Midway through, the head of operations asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Stack: Python and MLflow.

Results: The team stopped counting regressions reaching customers after they fell by 42%.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

If I did it again I would write the acceptance checks in the first week rather than the third.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.
