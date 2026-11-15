---
item_id: fullstack-cs-14
project_id: fullstack-p18
title: "AWS migration of a Django monolith"
date: 2026-01
client_industry: "media"
client_name: "Quarry Media"
engagement: fixed
price_usd: 1250
---
# AWS migration of a Django monolith

It started with a Monday-morning complaint. Quarry Media, a media company, needed to move a Django application off a single aging server onto managed cloud infrastructure with zero downtime, and the workaround everyone relied on had stopped scaling.

### What happened

Finance confirmed a 37% reduction in hosting cost by the end of the second month.

### How

Along the way, to keep things dependable there was a pipeline that blocks merges when checks fail. I leaned on Django for a model-driven back office with a generated admin site. Every step was logged, so failures could be traced in minutes. It meant fewer moving parts to monitor.

For presigned uploads to a storage bucket and a managed queue, I went with AWS. The client's team got terminal automation for repetitive server chores, documented in the handover notes. It paid for itself within the first sprint. What made it stick was notebooks promoted into packaged, importable modules.

Next, I chose Docker to deliver packaged environments that behave identically on laptops and servers, mostly because the team already knew it. The first version was deliberately plain, and we only added polish once people used it. Along the way I put in a relational database with transactions, constraints and JSON columns. We agreed the limits up front so nobody was surprised later.

The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.

Around the halfway mark the requirements shifted when the head of data learned that another team had a related need. I adjusted the design so both could share it.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

The team's questions in chat became the backlog. If someone asked the same thing twice, I turned it into a feature or a doc.

A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.

### Constraints

We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.

The client's team was split across three time zones, so decisions had to be written down rather than made in meetings.

Budget was tight, so I kept the moving parts few and avoided anything that needed a dedicated person to look after it.

The handover included a one-page troubleshooting guide covering the three failures we actually saw in testing.

Showing the client where the old numbers were wrong did more for trust than any promise.

Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.

Tools: AWS, Docker, and Django.
