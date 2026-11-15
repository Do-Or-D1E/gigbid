---
item_id: ai_ml-cs-01
project_id: ai_ml-p01
title: "Invoice field extraction for accounts payable"
date: 2022-09
client_industry: "fintech"
client_name: "Nimbus Ledger"
engagement: fixed
price_usd: 3750
---
# Invoice field extraction for accounts payable

What do you do when a fintech company has to pull vendor, date and amount fields out of scanned supplier invoices without anyone keying them in and nobody owns the problem? In September 2022, Nimbus Ledger asked me exactly that.

Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.

The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.

The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.

Key decisions:

- I leaned on FastAPI for an async web service with automatic request validation and generated interactive docs. I wrote nearly everything in Python. The client's engineers could read and change it without me.
- Then the design included a trained model wrapped behind a versioned, monitored HTTP endpoint. Later in the project I introduced extraction of company names, dates and amounts from unstructured paragraphs.
- I leaned on Docker for packaged environments that behave identically on laptops and servers. It paid for itself within the first sprint. Behind the scenes, digitised paper documents turned into machine-readable fields did the repetitive work. Every step was logged, so failures could be traced in minutes.

Roughly: 1 weeks to understand the data and agree the target, 2 weeks building, and the rest on testing with real users and documentation.

I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.

Weekly demos with real data mattered more than any slide deck; people trust what they can click.

The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.

Stack: Python, FastAPI, and Docker.

Results: The number that mattered: invoice processing dropped from half a day to 15 minutes. It ran through its first quarter-end without anyone having to step in.

A small, boring design that the team could maintain beat a more sophisticated one I had sketched first.

After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.
