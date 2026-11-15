---
item_id: data_analyst-cs-01
project_id: data_analyst-p02
title: "Marketing attribution cleanup"
date: 2024-07
client_industry: "SaaS"
client_name: "Keystone Software Co"
engagement: fixed
price_usd: 1700
---
# Marketing attribution cleanup

The previous contractor left Keystone Software Co with a half-finished attempt to work out which campaigns actually produce paying customers. My first job was working out what could be kept.

## The problem

Access to production was limited. I worked from a sanitised copy and checked every change against a staging environment first.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

## What I built

For partitioned tables queried at scale in Google's cloud, I went with BigQuery. It meant fewer moving parts to monitor. I wired in deduplication, standardisation and repair of malformed records before any analysis so the team would not have to think about it. I wrote checks around it before touching anything that depended on it. To keep things dependable there was queries that aggregate millions of rows with common table expressions.

In parallel, to keep things dependable there was step-by-step conversion rates from first visit to purchase. We agreed the limits up front so nobody was surprised later. Google Analytics 4 provided a tagged website whose sessions, events and audiences are visible in Google's measurement suite.

The head of data reviewed a working slice every few days, which caught two wrong assumptions early.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

Midway through, the head of data asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

The first 2 weeks went on discovery and a thin end-to-end slice. Weeks 3 to 7 were about hardening it, and the last week was handover.

## Stack

Google Analytics 4 and BigQuery.

## Results

Finance confirmed a 26% reduction in wasted ad spend by the end of the second month.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

I underestimated the time needed for the unglamorous parts: naming, documentation and cleaning up after failures.
