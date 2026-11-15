---
item_id: data_analyst-cs-15
project_id: data_analyst-p20
title: "Payment failure funnel"
date: 2025-08
client_industry: "fintech"
client_name: "Elmstead Bank Group"
engagement: fixed
price_usd: 900
---
# Payment failure funnel

What do you do when a fintech company has to find out why a fifth of card payments fail on the second attempt and nobody owns the problem? In August 2025, Elmstead Bank Group asked me exactly that.

The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

Mixpanel provided event-level product usage tracking with user properties. I wrote nearly everything in SQL.

Behind the scenes, careful treatment of variance, sample size and bias did the repetitive work. That kept the maintenance burden low for a team of two. It was also the cheapest option that met the performance target. Behind the scenes, control-versus-treatment experiments with significance checks did the repetitive work.

Along the way I put in step-by-step conversion rates from first visit to purchase. It fit the team's existing habits, which mattered more than elegance.

The tools involved were SQL and Mixpanel.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

Midway through, the founder asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

I paired with their one in-house developer for a day each week so the code would not become a black box.

We worked in one-week increments. By the end of week 1 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

Within eight weeks, recovered payment volume was up from $49k a month to $71k a month. Questions to the sales team about the old process stopped within a month.

Everything was left documented and monitored, with alerts going to the channel the team already watched.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.

Showing the client where the old numbers were wrong did more for trust than any promise.
