---
item_id: fullstack-cs-07
project_id: fullstack-p08
title: "Back-office admin for a law firm"
date: 2024-09
client_industry: "legal"
client_name: "Everly Partners"
engagement: hourly
price_usd: 2660
---
# Back-office admin for a law firm

Everly Partners needed to give staff one internal tool for matters, deadlines and client documents. They had already tried twice, once with an off-the-shelf tool and once in-house.

The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

The existing system could not be switched off during the work, which meant every change had to be backwards compatible.

First, I chose Django to deliver a model-driven back office with a generated admin site, mostly because the team already knew it. I wrote checks around it before touching anything that depended on it. The client's team got cross-browser end-to-end scripts that click through real user journeys on every pull request, documented in the handover notes. I compared two alternatives first, and this one was simpler to operate. It was also the cheapest option that met the performance target.

Hosted identity with social logins and role claims was part of the first milestone. That kept the maintenance burden low for a team of two. Carefully indexed tables with versioned migrations was part of the first milestone. I kept the interface small so the next developer would not have to learn my habits.

Towards the end, we also needed notebooks promoted into packaged, importable modules, so I added it early. Using React, I set up a single-page application assembled from reusable view components.

The tools involved were React and Django.

The first 1 weeks went on discovery and a thin end-to-end slice. Weeks 2 to 6 were about hardening it, and the last week was handover.

I kept a running decision log in a shared document, and it saved us at least one argument later.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

Before the change, matter set-up time took 4 days of somebody's week; afterwards it was 6 hours. New starters at Everly Partners picked it up from the documentation without needing a walkthrough.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.

The biggest saving came from deleting a step nobody needed, not from making a step faster.
