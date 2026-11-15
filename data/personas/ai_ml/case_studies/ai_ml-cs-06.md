---
item_id: ai_ml-cs-06
project_id: ai_ml-p07
title: "Essay feedback assistant"
date: 2024-10
client_industry: "edtech"
client_name: "Willow Learn Group"
engagement: fixed
price_usd: 4200
---
# Essay feedback assistant

The previous contractor left Willow Learn Group with a half-finished attempt to give students rubric-based feedback on draft essays within seconds. My first job was working out what could be kept.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.

Hugging Face Transformers sat at the centre of pretrained language models pulled from the open model hub. I compared two alternatives first, and this one was simpler to operate. It paid for itself within the first sprint. The second milestone added low-rank adapters trained on the client's domain data. I wrote checks around it before touching anything that depended on it. Using PyTorch, I set up hand-written training loops with mixed precision. It was also the cheapest option that met the performance target.

Once that was stable, part of the delivery was automatic routing of each inbound message to the right queue by predicted topic. It meant fewer moving parts to monitor. I wired in a pipeline that turns free-text tickets and emails into structured fields so the team would not have to think about it. That kept the maintenance burden low for a team of two.

The tools involved were Hugging Face Transformers and PyTorch.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

Midway through, the head of operations asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

The first 1 weeks went on discovery and a thin end-to-end slice. Weeks 2 to 3 were about hardening it, and the last week was handover.

Weekly demos with real data mattered more than any slide deck; people trust what they can click.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

Share of drafts reviewed without a teacher climbed to 51% by the second month. It ran through its first quarter-end without anyone having to step in.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.

If I did it again I would write the acceptance checks in the first week rather than the third.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.
