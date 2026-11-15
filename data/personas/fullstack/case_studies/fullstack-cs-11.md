---
item_id: fullstack-cs-11
project_id: fullstack-p14
title: "Itinerary sharing app"
date: 2022-11
client_industry: "travel"
client_name: "Pelican Travel"
engagement: fixed
price_usd: 3500
---
# Itinerary sharing app

The previous contractor left Pelican Travel with a half-finished attempt to let friends plan a trip together and see each other's edits as they happen. My first job was working out what could be kept.

A trade show fixed the delivery date, which left almost no slack for surprises.

Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

In parallel, later in the project I introduced hosted identity with social logins and role claims. On the Tailwind CSS side, the work was a consistent look built from atomic classes instead of custom stylesheets. I compared two alternatives first, and this one was simpler to operate. I chose Firebase to deliver serverless data sync for web and phone clients, mostly because the team already knew it. We agreed the limits up front so nobody was surprised later. It was also the cheapest option that met the performance target.

The design included a bidirectional channel for notifications. I leaned on React for a client-side app that re-renders only what changed.

The tools involved were React, Firebase, and Tailwind CSS.

Midway through, the programme director asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.

Roughly: 3 weeks to understand the data and agree the target, 4 weeks building, and the rest on testing with real users and documentation.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

Before launch we ran old and new side by side for a fortnight. The differences we found were almost all bugs in the old process, which was a useful surprise.

The programme director reviewed a working slice every few days, which caught two wrong assumptions early.

Share of trips planned collaboratively climbed to 76% by the second month.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.

Showing the client where the old numbers were wrong did more for trust than any promise.
