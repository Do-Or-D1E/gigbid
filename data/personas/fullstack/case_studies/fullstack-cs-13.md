---
item_id: fullstack-cs-13
project_id: fullstack-p17
title: "Single sign-on retrofit"
date: 2023-03
client_industry: "fintech"
client_name: "Lighthouse Credit"
engagement: hourly
price_usd: 6490
---
# Single sign-on retrofit

Lighthouse Credit needed to add company single sign-on to a legacy internal app without breaking existing logins. They had already tried twice, once with an off-the-shelf tool and once in-house.

**Situation.** We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

**Approach.** For sign-in with Google and company single sign-on, I went with OAuth. It fit the team's existing habits, which mattered more than elegance. A fast test suite guarding the business logic was part of the first milestone. Express provided a minimal HTTP routing layer with middleware chains. It meant fewer moving parts to monitor.

Towards the end, to keep things dependable there was a compose file that brings up the whole stack with one command. It was also the cheapest option that met the performance target. Later in the project I introduced session handling without server-side session storage. I compared two alternatives first, and this one was simpler to operate. I wrote checks around it before touching anything that depended on it.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

The founder reviewed a working slice every few days, which caught two wrong assumptions early.

Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.

Midway through, the founder asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

**Stack:** OAuth and Express

**Result.** The team stopped counting password-reset requests after they fell by 31%. It ran through its first quarter-end without anyone having to step in.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.
