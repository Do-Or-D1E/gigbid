---
item_id: fullstack-cs-03
project_id: fullstack-p03
title: "Custom Shopify storefront for a skincare brand"
date: 2024-12
client_industry: "e-commerce"
client_name: "Umber Cart"
engagement: hourly
price_usd: 2140
---
# Custom Shopify storefront for a skincare brand

23.9% to 28.1%. That was the headline number when Umber Cart signed off on the finished work. Getting there meant working out how to replace a slow off-the-shelf theme with a fast, branded storefront.

### What happened

Within eight weeks, mobile conversion rate was up from 23.9% to 28.1%. It ran through its first quarter-end without anyone having to step in.

### How

Then for a hosted storefront with custom theme code and app integrations, I went with Shopify. We agreed the limits up front so nobody was surprised later. A key piece was resource-oriented HTTP endpoints with versioning and pagination. It meant fewer moving parts to monitor.

Mobile-first page layouts without a UI kit was part of the first milestone. It paid for itself within the first sprint. Most of the day-to-day work happened in JavaScript. I kept the interface small so the next developer would not have to learn my habits. That kept the maintenance burden low for a team of two.

Around the halfway mark the requirements shifted when the head of operations learned that another team had a related need. I adjusted the design so both could share it.

Weekly demos with real data mattered more than any slide deck; people trust what they can click.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.

The first 3 weeks went on discovery and a thin end-to-end slice. Weeks 4 to 11 were about hardening it, and the last week was handover.

### Constraints

Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.

Budget was tight, so I kept the moving parts few and avoided anything that needed a dedicated person to look after it.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

I underestimated the time needed for the unglamorous parts: naming, documentation and cleaning up after failures.

They kept the system running themselves after the first month, and I was only pulled back in for a small extension.

Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.

Tools: Shopify and JavaScript.
