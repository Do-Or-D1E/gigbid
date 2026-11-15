---
item_id: ai_ml-cs-07
project_id: ai_ml-p08
title: "Clinic note summariser"
date: 2024-06
client_industry: "healthcare"
client_name: "Driftwood Clinic"
engagement: fixed
price_usd: 2450
---
# Clinic note summariser

Nobody at Driftwood Clinic had the time to turn long free-text clinic notes into short structured handover summaries, so they hired a contractor. That was me, for about 14 weeks.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

There was no baseline. Nobody had measured how long the old process took, so I started by timing it myself over a week.

Key decisions:

- Next, we standardised on LangGraph, which handled an agent workflow with explicit branches, loops and human-approval steps. I wrote checks around it before touching anything that depended on it. I wired in systematic wording and structure tweaks to get reliable model output so the team would not have to think about it. The first version was deliberately plain, and we only added polish once people used it.
- I wired in golden test sets that catch prompt regressions so the team would not have to think about it. Extraction of company names, dates and amounts from unstructured paragraphs was part of the first milestone. It fit the team's existing habits, which mattered more than elegance. The client's engineers could read and change it without me.
- OpenAI API gave us structured JSON output from a commercial language-model endpoint.

Roughly: 3 weeks to understand the data and agree the target, 4 weeks building, and the rest on testing with real users and documentation.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

Weekly demos with real data mattered more than any slide deck; people trust what they can click.

Midway through, the programme director asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Stack: OpenAI API and LangGraph.

Results: Before the change, shift handover prep took a full week of somebody's week; afterwards it was a single afternoon.

Everything was left documented and monitored, with alerts going to the channel the team already watched.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.

I underestimated the time needed for the unglamorous parts: naming, documentation and cleaning up after failures.
