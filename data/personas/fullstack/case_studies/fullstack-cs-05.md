---
item_id: fullstack-cs-05
project_id: fullstack-p05
title: "Clinic appointment booking"
date: 2022-07
client_industry: "healthcare"
client_name: "Elmstead Health Group"
engagement: fixed
price_usd: 2400
---
# Clinic appointment booking

In July 2022, Elmstead Health Group came to me with a deadline and a short brief: let patients book, move and cancel appointments online and cut front-desk phone calls.

**Situation.** Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.

**Approach.** Behind the scenes, coverage gates enforced on every merge did the repetitive work. I compared two alternatives first, and this one was simpler to operate. PostgreSQL gave us carefully indexed tables with versioned migrations. It meant fewer moving parts to monitor. We also needed hosted identity with social logins and role claims, so I added it early. I kept the interface small so the next developer would not have to learn my habits. That kept the maintenance burden low for a team of two.

TypeScript was the main working language throughout. The first version was deliberately plain, and we only added polish once people used it. The core of it was NestJS: controllers, providers and guards organised into feature modules.

A key piece was session handling without server-side session storage. We agreed the limits up front so nobody was surprised later.

We worked in one-week increments. By the end of week 1 there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

Their CTO reviewed a working slice every few days, which caught two wrong assumptions early.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

Around the halfway mark the requirements shifted when their CTO learned that another team had a related need. I adjusted the design so both could share it.

**Stack:** NestJS, PostgreSQL, and TypeScript

**Result.** Share of bookings made online climbed to 50% by the second month. New starters at Elmstead Health Group picked it up from the documentation without needing a walkthrough.

I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.

If I did it again I would write the acceptance checks in the first week rather than the third.

Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.
