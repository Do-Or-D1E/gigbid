---
item_id: data_analyst-cs-06
project_id: data_analyst-p07
title: "Staff engagement survey"
date: 2025-09
client_industry: "healthcare"
client_name: "Dovetail Wellness Co"
engagement: hourly
price_usd: 3110
---
# Staff engagement survey

Companies in healthcare rarely get to choose their data or their tooling, and Dovetail Wellness Co was no exception. The ask was simple on paper: turn 4,000 free-text and rating responses from a hospital group's staff survey into a board-ready report.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

The client's team was split across three time zones, so decisions had to be written down rather than made in meetings.

Deduplication, standardisation and repair of malformed records before any analysis was part of the first milestone. That kept the maintenance burden low for a team of two. Confidence intervals and significance tests on messy samples was part of the first milestone.

I leaned on Excel for pivot tables and lookup formulas in workbooks. It fit the team's existing habits, which mattered more than elegance. To keep things dependable there was clear charts that make a trend obvious at a glance.

We standardised on survey analysis, which handled coded open-ended answers and rating-scale summaries.

The tools involved were Excel and survey analysis.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

Midway through, the programme director asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

The first 3 weeks went on discovery and a thin end-to-end slice. Weeks 4 to 12 were about hardening it, and the last week was handover.

The number that mattered: survey reporting turnaround dropped from 3 days to 5 hours. The programme director told me later that it was the first time the numbers were never argued about in a meeting.

Everything was left documented and monitored, with alerts going to the channel the team already watched.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.
