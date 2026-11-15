---
item_id: data_analyst-cs-09
project_id: data_analyst-p13
title: "Product analytics for a mobile app"
date: 2024-09
client_industry: "media"
client_name: "Marlow Network"
engagement: fixed
price_usd: 650
---
# Product analytics for a mobile app

What do you do when a media company has to find where new users drop out of the first week of a news app and nobody owns the problem? In September 2024, Marlow Network asked me exactly that.

## Why they called me

The existing system could not be switched off during the work, which meant every change had to be backwards compatible.

Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.

A trade show fixed the delivery date, which left almost no slack for surprises.

## How it went

The design included control-versus-treatment experiments with significance checks. The codebase was mostly SQL. We agreed the limits up front so nobody was surprised later. We also needed signup-month cohorts tracked for how many users stay active, so I added it early. I wrote checks around it before touching anything that depended on it.

I wired in step-by-step conversion rates from first visit to purchase so the team would not have to think about it. It paid for itself within the first sprint. I leaned on Mixpanel for in-app event streams turned into usage graphs. It was also the cheapest option that met the performance target.

Midway through, the head of data asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

The head of data reviewed a working slice every few days, which caught two wrong assumptions early.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.

## Under the hood

Mixpanel and SQL.

## The numbers

Within eight weeks, week-one retention was up from 9.1% to 10.3%. It ran through its first quarter-end without anyone having to step in.

At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.

Agreeing on definitions early saved more time than any clever optimisation.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.
