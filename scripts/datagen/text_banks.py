"""Large text banks used by the persona and job generators. ASCII only."""
from __future__ import annotations

INDUSTRIES = {
    "fintech": dict(label="fintech", ent="transaction", table="transactions",
                    biz=["a payments startup", "a small online lender", "a neobank for freelancers", "a card-issuing platform",
                         "an invoice-financing company"],
                    suffix=["Pay", "Ledger", "Capital", "Finance", "Credit", "Bank"]),
    "healthcare": dict(label="healthcare", ent="appointment", table="appointments",
                       biz=["a group of dental clinics", "a telehealth startup", "a medical-device distributor",
                            "a physiotherapy chain", "a diagnostics lab network"],
                       suffix=["Health", "Care", "Clinic", "Medical", "Wellness"]),
    "ecommerce": dict(label="e-commerce", ent="order", table="orders",
                      biz=["an online store selling home goods", "a direct-to-consumer skincare brand",
                           "a marketplace for handmade furniture", "a subscription snack box company",
                           "a sneaker resale shop"],
                      suffix=["Goods", "Market", "Shop", "Supply", "Cart", "Co"]),
    "logistics": dict(label="logistics", ent="shipment", table="shipments",
                      biz=["a regional freight broker", "a last-mile delivery company", "a cold-chain transport firm",
                           "a warehouse and fulfilment operator", "a courier startup"],
                      suffix=["Freight", "Logistics", "Cargo", "Haul", "Route", "Transit"]),
    "edtech": dict(label="edtech", ent="student", table="students",
                   biz=["an online coding bootcamp", "a tutoring marketplace", "a language-learning app",
                        "a network of private schools", "a corporate training provider"],
                   suffix=["Academy", "Learn", "Campus", "Tutors", "Scholar"]),
    "real_estate": dict(label="real estate", ent="listing", table="listings",
                        biz=["a property agency", "a rental platform", "a commercial real-estate broker",
                             "a short-stay property manager", "a home-valuation startup"],
                        suffix=["Homes", "Estates", "Realty", "Properties", "Living"]),
    "legal": dict(label="legal", ent="matter", table="matters",
                  biz=["a mid-sized law firm", "a legal-tech startup", "a contract-management company",
                       "an immigration services office", "a compliance consultancy"],
                  suffix=["Legal", "Law", "Counsel", "Advisory", "Partners"]),
    "media": dict(label="media", ent="article", table="articles",
                  biz=["a digital news publisher", "a podcast network", "a video streaming startup",
                       "a magazine group", "a creator-economy newsletter business"],
                  suffix=["Media", "Press", "Studios", "Daily", "Network"]),
    "saas": dict(label="SaaS", ent="account", table="accounts",
                 biz=["a B2B software company", "a project-management SaaS startup", "a customer-support software vendor",
                      "a HR software company", "a subscription analytics tool"],
                 suffix=["Cloud", "Labs", "Systems", "Software", "Works", "Stack"]),
    "nonprofit": dict(label="nonprofit", ent="donation", table="donations",
                      biz=["a conservation charity", "a food-bank network", "a community education nonprofit",
                           "a disaster-relief organisation", "a youth mentoring charity"],
                      suffix=["Foundation", "Trust", "Alliance", "Initiative", "Fund"]),
    "manufacturing": dict(label="manufacturing", ent="part", table="parts",
                          biz=["a plastics moulding factory", "a furniture manufacturer", "an auto-parts supplier",
                               "a packaging company", "a textile mill"],
                          suffix=["Industries", "Works", "Fabrication", "Manufacturing", "Mills"]),
    "travel": dict(label="travel", ent="booking", table="bookings",
                   biz=["a boutique tour operator", "a hotel group", "a travel-booking startup",
                        "an events and ticketing company", "a car-rental business"],
                   suffix=["Travel", "Journeys", "Tours", "Voyages", "Stays"]),
    "energy": dict(label="energy", ent="meter", table="meters",
                   biz=["a regional electricity retailer", "a solar installer", "a utility analytics company"],
                   suffix=["Energy", "Power", "Grid", "Solar"]),
}

CLIENT_FIRST = ["Northgate", "Brightline", "Harbor", "Kestrel", "Maple", "Quill", "Tidewater", "Alder", "Cobalt",
                "Juniper", "Pinecrest", "Summit", "Larkspur", "Redwood", "Ironbridge", "Seaward", "Fernhill",
                "Marlow", "Oakhurst", "Silverline", "Bluefin", "Copperleaf", "Driftwood", "Elmstead", "Foxglove",
                "Greystone", "Hawthorn", "Ivory", "Kingsway", "Lighthouse", "Meridian", "Nimbus", "Orchard",
                "Pelican", "Quarry", "Ridgeway", "Saffron", "Thistle", "Umber", "Vantage", "Willow", "Zephyr",
                "Aspen", "Beacon", "Cascade", "Dovetail", "Everly", "Falcon", "Granite", "Halcyon", "Indigo",
                "Jasper", "Keystone", "Lumen", "Monarch", "Nova", "Onyx", "Prairie", "Rivet", "Sable"]

PERSON_FIRST = ["Sarah", "Daniel", "Priya", "Marcus", "Elena", "James", "Aisha", "Tom", "Lucia", "Kevin", "Nadia",
                "Oliver", "Mei", "Carlos", "Hannah", "Ravi", "Sofia", "Ben", "Fatima", "Nina", "Greg", "Amara",
                "Paul", "Yuki", "Diego", "Rachel", "Ahmed", "Claire", "Victor", "Ingrid", "Jamal", "Olga"]
PERSON_LAST = ["Brooks", "Chen", "Patel", "Novak", "Rossi", "Hughes", "Okafor", "Lindgren", "Silva", "Meyer",
               "Haddad", "Kowalski", "Tanaka", "Reyes", "Foster", "Iyer", "Duarte", "Walsh", "Bianchi", "Nguyen"]

COUNTRIES = ["United States", "United Kingdom", "Canada", "Australia", "Germany", "Netherlands", "United Arab Emirates",
             "Singapore", "Sweden", "Ireland", "France", "Spain", "Israel", "New Zealand", "Denmark"]

# ---------------------------------------------------------------- metrics
# nums: a,b strings; pct int. Templates use {noun} {a} {b} {pct}
MET = {
    "time": dict(
        cs=["{Noun} used to take about {a}. After the rollout it took {b}.",
            "The number that mattered: {noun} dropped from {a} to {b}.",
            "Before the change, {noun} took {a} of somebody's week; afterwards it was {b}."],
        nf=["{A} down to {b}.", "{A} became {b}."],
        prop=["took {noun} from {a} to {b}", "cut {noun} from {a} down to {b}"],
        rev=["{noun} went from {a} to {b}", "something that took us {a} now takes {b}"],
    ),
    "accuracy": dict(
        cs=["Measured on a held-out month, {noun} rose from {a} to {b}.",
            "{Noun} improved from {a} to {b} on data the model had never seen.",
            "Against the old rules-based process, {noun} went from {a} to {b}."],
        nf=["{A} to {b}.", "From {a} to {b}."],
        prop=["lifted {noun} from {a} to {b}", "raised {noun} to {b} (from {a})"],
        rev=["{noun} jumped from {a} to {b}", "{noun} is now around {b}, up from {a}"],
    ),
    "cost": dict(
        cs=["{Noun} fell by roughly {pct}% over the first quarter after launch.",
            "Finance confirmed a {pct}% reduction in {noun} by the end of the second month.",
            "{Noun} came down {pct}% compared with the same period a year earlier."],
        nf=["{Pct} percent less {noun}.", "A {pct}% cut in {noun}."],
        prop=["reduced {noun} by about {pct}%", "brought {noun} down {pct}%"],
        rev=["{noun} dropped by around {pct}%", "we saw {noun} fall {pct}% in the first quarter"],
    ),
    "revenue": dict(
        cs=["{Noun} improved from {a} to {b} in the weeks after launch.",
            "Within eight weeks, {noun} was up from {a} to {b}.",
            "The change showed up in the numbers: {noun} moved from {a} to {b}."],
        nf=["{A} to {b}.", "Up from {a} to {b}."],
        prop=["moved {noun} from {a} to {b}", "improved {noun} from {a} to {b}"],
        rev=["{noun} went from {a} to {b}", "our {noun} is up from {a} to {b}"],
    ),
    "volume": dict(
        cs=["{Noun} reached about {pct}% within a month of launch.",
            "By the end of the engagement the {noun} stood at {pct}%.",
            "{Noun} climbed to {pct}% by the second month."],
        nf=["{Noun} at {pct}%.", "{Pct}% on the {noun}."],
        prop=["got the {noun} up to about {pct}%", "pushed the {noun} to {pct}%"],
        rev=["the {noun} is now around {pct}%", "we reached {pct}% on the {noun}"],
    ),
    "errors": dict(
        cs=["{Noun} fell by {pct}% in the first full quarter.",
            "Tracked over three months, {noun} dropped {pct}%.",
            "The team stopped counting {noun} after they fell by {pct}%."],
        nf=["{Pct} percent fewer {noun}.", "{Noun}: down {pct}%."],
        prop=["cut {noun} by about {pct}%", "reduced {noun} by {pct}%"],
        rev=["{noun} dropped by about {pct}%", "we have {pct}% fewer {noun} now"],
    ),
}

# --------------------------------------------------------- case study banks
QUOTES = [
    "We were losing a day a week to this and nobody had time to fix it.",
    "We had tried a plug-in and an intern, and neither stuck.",
    "If it works on a Monday morning with no one watching, that is a win.",
    "Our old process only worked because one person remembered how it ran.",
    "I do not need it clever. I need it to run every day and tell me when it does not.",
    "We kept getting three different answers to the same question.",
    "Our customers noticed the problem before we did, and that was the wake-up call.",
    "The board wants a number by the end of the quarter and right now we cannot produce one.",
]

OPENERS = [
    "It started with a Monday-morning complaint. {Client}, {a_ind} company, needed to {need}, and the workaround everyone relied on had stopped scaling.",
    "\"{quote}\" That was the first thing {contact} at {client} said to me, and it set the tone for the whole engagement.",
    "{Nf} That was the headline number when {client} signed off on the finished work. Getting there meant working out how to {need}.",
    "{Client} needed to {need}. They had already tried twice, once with an off-the-shelf tool and once in-house.",
    "I joined {client} as the only {role} on a team of {n} and was asked to {need} inside a single quarter.",
    "What do you do when {a_ind} company has to {need} and nobody owns the problem? In {monthyear}, {client} asked me exactly that.",
    "Companies in {ind} rarely get to choose their data or their tooling, and {client} was no exception. The ask was simple on paper: {need}.",
    "In {monthyear}, {client} came to me with a deadline and a short brief: {need}.",
    "The brief had three constraints: a fixed budget, a small team and a hard date. Inside them, {client} wanted to {need}.",
    "The previous contractor left {client} with a half-finished attempt to {need}. My first job was working out what could be kept.",
    "Looking back, the interesting part of the {client} project was not the technology. It was agreeing what it meant to {need}, and how we would know it worked.",
    "Project summary. Client: {client} ({ind}). Goal: {need}. Engagement: {engagement}, starting {monthyear}.",
    "Nobody at {client} had the time to {need}, so they hired a contractor. That was me, for about {weeks} weeks.",
]

CONTACTS = ["the head of operations", "the product owner", "their CTO", "the finance lead", "the founder",
            "the operations manager", "the head of data", "the programme director"]

CHALLENGES = [
    "The source data was messier than anyone had admitted: duplicate records, free-text fields and three different date formats in the same table.",
    "Two stakeholders disagreed about what success looked like, so the first week went on writing it down and getting both signatures.",
    "The existing system could not be switched off during the work, which meant every change had to be backwards compatible.",
    "The team had no spare capacity, so everything I built had to be understandable by someone who had never seen it.",
    "Access to production was limited. I worked from a sanitised copy and checked every change against a staging environment first.",
    "Volumes in the pilot were small but would be about ten times larger in real use, and the design had to survive that.",
    "A trade show fixed the delivery date, which left almost no slack for surprises.",
    "There was no baseline. Nobody had measured how long the old process took, so I started by timing it myself over a week.",
    "Part of the history lived in email attachments and one person's laptop, and recovering it took longer than the build.",
    "Compliance wanted every decision to be explainable after the fact, which shaped a lot of the design.",
    "The client's team was split across three time zones, so decisions had to be written down rather than made in meetings.",
    "Budget was tight, so I kept the moving parts few and avoided anything that needed a dedicated person to look after it.",
]

COLLAB = [
    "We met twice a week for thirty minutes, and I posted a short written update every Friday so nobody had to guess where things stood.",
    "{Contact} reviewed a working slice every few days, which caught two wrong assumptions early.",
    "I kept a running decision log in a shared document, and it saved us at least one argument later.",
    "Weekly demos with real data mattered more than any slide deck; people trust what they can click.",
    "The team's questions in chat became the backlog. If someone asked the same thing twice, I turned it into a feature or a doc.",
    "I paired with their one in-house developer for a day each week so the code would not become a black box.",
]

LESSONS = [
    "If I did it again I would write the acceptance checks in the first week rather than the third.",
    "The biggest saving came from deleting a step nobody needed, not from making a step faster.",
    "Agreeing on definitions early saved more time than any clever optimisation.",
    "I underestimated the time needed for the unglamorous parts: naming, documentation and cleaning up after failures.",
    "A small, boring design that the team could maintain beat a more sophisticated one I had sketched first.",
    "Showing the client where the old numbers were wrong did more for trust than any promise.",
    "Next time I would ask for a sample of the worst data on day one instead of the average data.",
]

HANDOFF = [
    "At the end I wrote a short runbook, recorded a walkthrough and left the repository in a state their own developer could pick up.",
    "The handover included a one-page troubleshooting guide covering the three failures we actually saw in testing.",
    "I stayed on for two weeks of light support, and the only ticket in that period was a typo in a label.",
    "They kept the system running themselves after the first month, and I was only pulled back in for a small extension.",
    "Everything was left documented and monitored, with alerts going to the channel the team already watched.",
]

HEAD_SETS = [
    ("The problem", "What I built", "Stack", "Results"),
    ("Background", "Approach", "Tools", "Outcome"),
    ("Context", "The work", "Technology", "What changed"),
    ("Why they called me", "How it went", "Under the hood", "The numbers"),
    ("Situation", "Plan and delivery", "Toolbox", "Impact"),
]

TRANS = ["First, ", "Next, ", "After that, ", "Once that was stable, ", "In parallel, ", "Towards the end, ",
         "Early on, ", "Then ", "Along the way, ", ""]

NAMED_USE = [
    "{Name} provided {np}.",
    "For {np}, I went with {name}.",
    "I chose {name} to deliver {np}, mostly because the team already knew it.",
    "{Name} gave us {np}.",
    "We standardised on {name}, which handled {np}.",
    "Using {name}, I set up {np}.",
    "{Name} sat at the centre of {np}.",
    "I leaned on {name} for {np}.",
    "The core of it was {name}: {np}.",
    "On the {name} side, the work was {np}.",
]

IMPLIED_USE = [
    "The design included {np}.",
    "Along the way I put in {np}.",
    "A key piece was {np}.",
    "We also needed {np}, so I added it early.",
    "To keep things dependable there was {np}.",
    "Behind the scenes, {np} did the repetitive work.",
    "I wired in {np} so the team would not have to think about it.",
    "The client's team got {np}, documented in the handover notes.",
    "There was also {np}, which turned out to matter more than expected.",
    "Later in the project I introduced {np}.",
    "{Np} was part of the first milestone.",
    "Part of the delivery was {np}.",
    "The second milestone added {np}.",
    "What made it stick was {np}.",
]

# ------------------------------------------------------------ review banks
REV_OPEN = {
    5: ["{first} delivered exactly what we asked for and a bit more.",
        "Great experience from start to finish. {first} understood the problem quickly.",
        "I would hire {first} again without hesitation.",
        "Clear communication, steady progress and no surprises.",
        "Honestly the best contractor we have worked with this year.",
        "{first} asked the right questions before writing any code."],
    4: ["Good work overall. {first} was reliable and the result does what we needed.",
        "Solid delivery, a couple of small delays but handled openly.",
        "Happy with the result. The scope grew a little and {first} handled it professionally.",
        "Very capable and easy to work with, only minor rough edges at handover."],
    3: ["The end result works, but it took more back-and-forth than I expected.",
        "Decent outcome. Communication was patchy for the first two weeks.",
        "Delivered what was agreed, though some parts needed rework after our testing.",
        "Mixed feelings: the technical side was fine, the timeline slipped."],
    2: ["Delivered late and needed several rounds of fixes before we could use it.",
        "The core idea was good but the handover was weak and I had to chase for updates.",
        "Not the experience I hoped for. Parts of it still need work."],
}
REV_SKILL = [
    "The setup includes {np}, and it has been running without trouble.",
    "What impressed us was {np}; we would not have thought to ask for it.",
    "{first} built {np}, which our team now relies on.",
    "Our engineers were glad to find {np} in the handover.",
    "The part we use most is {np}.",
    "There is also {np}, which saved us a lot of manual effort.",
]
REV_END = [
    "Recommended.", "Would work with again.", "Thanks for the help.", "Five stars from us.",
    "Will probably bring {first} back for phase two.", "Communication was prompt throughout.",
    "", "", "",
]
REV_END_LOW = ["Would need a clearer plan next time.", "I would give it another chance with tighter milestones.",
               "Hopefully the next engagement goes more smoothly.", ""]

# -------------------------------------------------------- proposals banks
GENERIC_OPEN = [
    "Dear Sir/Madam, I am writing to apply for the position advertised on your platform.",
    "Hello, I am excited to apply for this job. I am a hardworking and passionate {role}.",
    "I'm passionate about {field} and I would love to work on your project.",
    "Hi, I read your job description and I am confident that I am the best fit for this position.",
    "Greetings! I can do this job. I have many years of experience and I am a fast learner.",
    "Dear Hiring Manager, I am interested in your job and I believe I have the skills required.",
    "Hello sir, I saw your job posting and I want to work with you. I am available immediately.",
    "I am writing to express my interest in this opportunity. I am a dedicated professional with strong skills.",
]
GENERIC_BODY = [
    "I have extensive experience with {skills} and many other technologies, and I always deliver quality work on time.",
    "I have worked on many similar projects for clients around the world and they were all very satisfied.",
    "I am a team player with excellent communication skills and a strong work ethic. I will give 100% to your project.",
    "My skills include {skills}. I am sure I can complete your project to your satisfaction.",
    "I guarantee that you will be happy with my work. Please give me a chance to prove myself.",
]
GENERIC_CLOSE = [
    "Looking forward to hearing from you. Thank you.",
    "Please let me know if you are interested. Best regards.",
    "I am ready to start right now. Thanks for your time.",
    "Kindly consider my application. Thank you very much.",
    "Hope to work with you. Regards.",
]

MID_OPEN = [
    "Hi, thanks for posting. This looks like a good match for my background in {category}.",
    "Hello, I have done similar {category} work before and your project seems straightforward.",
    "Hi there, I do a lot of {category} projects and would be happy to help with this one.",
    "Thanks for the details. I work in {category} and have a few examples I could share.",
]

HOOK_OPEN = [
    "You want to {task}. The part of your post about {detail} is where projects like this usually go wrong, so let me be concrete about how I would handle it.",
    "I read your brief twice. The goal to {task} is clear, and {detail} is the detail I would settle first.",
    "Quick thought on your post: to {task} reliably you need {detail} sorted before anything else.",
    "{Detail} is the line in your post that caught my attention, because it is usually what decides whether an effort to {task} sticks.",
    "Your note about {detail} tells me you have been burned before. Here is how I would {task} without repeating that.",
    "Straight to it: you want to {task}. I have solved a close cousin of that problem, and {detail} is the part I would plan around.",
    "To {task}, I would start where your post points: {detail}.",
]

PLAN = [
    "My plan: a short call to confirm scope, a first working slice within {d1} days so you can react to something real, then {d2} days of hardening and handover.",
    "I would split this into two milestones. The first covers the core path end to end, the second covers edge cases, monitoring and documentation.",
    "Proposed approach: start with a small audit of what you already have, agree the success measure with you in writing, then build in weekly increments you can review.",
    "I work in small deliverables: you would see something running in the first week, and I would keep a short written update every Friday.",
    "Rough timeline: about {weeks} weeks, with a demo at the end of each week and a clean handover with documentation.",
]
QUESTIONS = [
    "One question: how are you handling this today, and what breaks most often?",
    "Do you already have sample data or a staging environment I could use from day one?",
    "Who will review the first version on your side, and how quickly can they give feedback?",
    "What would you consider a successful result in the first month?",
    "Is there an existing system I need to stay compatible with?",
    "Do you have a hard deadline I should plan around?",
]
CLOSE = [
    "Happy to start this week if the scope looks right to you.",
    "If this sounds close to what you need, I can send a short written plan before we agree anything.",
    "I can start on Monday and keep the first milestone small so you can judge the fit with little risk.",
    "Let me know if you would like a brief call first. I am flexible on time zones.",
    "Glad to answer any questions here in the platform chat.",
]
EVID_INTRO = [
    "I recently did something close to this for {a_ind} client: {need}.",
    "Relevant experience: for {a_ind} company I worked on a very similar problem, namely to {need}.",
    "A comparable project: {a_ind} team needed to {need}.",
    "I have solved a close cousin of this. For {a_ind} business the goal was to {need}.",
    "Last year {a_ind} client asked me to {need}, which maps closely to what you describe.",
]
EVID_RESULT = [
    "The outcome: I {prop}.",
    "Result: I {prop}.",
    "In the end I {prop}.",
]
