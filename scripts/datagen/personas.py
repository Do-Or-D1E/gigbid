"""Persona generator: projects, case studies, repos, reviews, proposals, CV and gold labels."""
from __future__ import annotations

import collections
import datetime as dt
import json
import math
import random

from . import archetypes as AR
from . import code_snippets as CS
from . import text_banks as TB
from .persona_specs import CATEGORIES, PROFILES, PROJECT_SPECS
from .taxonomy import BASE
from .util import (a_an, cap, chance, has_term, iso_dt, join_and, month_str, nwords, pick, pick_n, rand_date, slugify,
                   weighted)

REASONS = [
    "That kept the maintenance burden low for a team of two.",
    "It was also the cheapest option that met the performance target.",
    "The client's engineers could read and change it without me.",
    "It meant fewer moving parts to monitor.",
    "I compared two alternatives first, and this one was simpler to operate.",
    "It fit the team's existing habits, which mattered more than elegance.",
    "Every step was logged, so failures could be traced in minutes.",
    "I wrote checks around it before touching anything that depended on it.",
    "It paid for itself within the first sprint.",
    "We agreed the limits up front so nobody was surprised later.",
    "The first version was deliberately plain, and we only added polish once people used it.",
    "I kept the interface small so the next developer would not have to learn my habits.",
]
LANG_USE = [
    "The codebase was mostly {name}.", "{Name} was the main working language throughout.",
    "Most of the day-to-day work happened in {name}.", "I wrote nearly everything in {name}.",
    "Everything custom was written in {name}.",
]
TIMELINES = [
    "The first {w1} weeks went on discovery and a thin end-to-end slice. Weeks {w2} to {w3} were about hardening it, and the last week was handover.",
    "Roughly: {w1} weeks to understand the data and agree the target, {w2} weeks building, and the rest on testing with real users and documentation.",
    "We worked in one-week increments. By the end of week {w1} there was something people could click or query, and the remaining time was spent on the cases nobody had mentioned at the start.",
    "The calendar looked like this: a short discovery phase, a long middle where most of the building happened, and a deliberate two-week buffer before launch that we ended up using.",
]
SCOPE = [
    "Midway through, {contact} asked for an extra feature that was not in the original brief. We agreed to swap it for something lower priority, so the date stayed put.",
    "Around the halfway mark the requirements shifted when {contact} learned that another team had a related need. I adjusted the design so both could share it.",
    "One unplanned detour: an upstream system changed its export format in week five. Because I had isolated that part, the fix took an afternoon.",
]
OUTCOMES_EXTRA = [
    "Questions to the {team} about the old process stopped within a month.",
    "{Contact} told me later that it was the first time the numbers were never argued about in a meeting.",
    "The client asked for a second phase before the first one had finished.",
    "New starters at {client} picked it up from the documentation without needing a walkthrough.",
    "It ran through its first quarter-end without anyone having to step in.",
]
TESTING = [
    "Testing was split three ways: automated checks on the logic, a replay of last month's real data, and a two-day trial with the people who would use it every day.",
    "Before launch we ran old and new side by side for a fortnight. The differences we found were almost all bugs in the old process, which was a useful surprise.",
    "I kept a list of the ugliest real-world inputs, such as blank fields, duplicate rows and strange encodings, and turned each one into a repeatable check.",
    "Acceptance was simple: five agreed scenarios, each signed off by the person who owned that part of the business.",
]
RISKS = [
    "The main risk was adoption rather than technology. People only trust a new system once it has been right a few times, so I made the first release read-only and let them compare.",
    "A second risk was a single point of failure in how the data arrived. I added alerts and a fallback so a bad day upstream would not become a bad day for the client.",
    "There was a real chance the whole thing would be too slow at full volume, so I load-tested it early with a synthetic copy ten times the size.",
    "Cost was the other worry. I put a ceiling on what the system could spend and agreed in advance what would happen if it got close.",
]
POSTLAUNCH = [
    "After launch I watched the first three weeks closely: a short daily check, a weekly summary for the client, and a list of small fixes shipped each Friday.",
    "Once it was live, usage grew faster than anyone predicted, and a few of the small decisions we made early, such as clear names and sensible defaults, paid off.",
    "Feedback after the first month shaped a small second phase: two new views, a couple of fixes and better documentation of the edge cases.",
    "Post-launch support was light. The questions that did come in were about how to read the output, so I added a short explainer next to it.",
]
DATA_NOTES = [
    "The inputs came from three places that had never been compared before, and the first useful deliverable was simply a list of where they disagreed.",
    "Roughly a tenth of the records needed manual judgement, so I built a small review queue for the client's staff rather than guessing.",
    "We agreed a naming convention in week one and stuck to it, which made every later conversation shorter.",
    "Nothing sensitive left the client's environment. I worked against a masked copy and documented every field I touched.",
]
OUT_A, OUT_B, OUT_C, OUT_D = 0.5, -1.15, 0.3, -1.5
TEAM = ["support team", "finance team", "operations team", "sales team", "editorial desk"]
DETAILS = [
    "the nightly job that fails without telling anyone", "numbers that differ between teams",
    "a manual copy-paste step that eats Friday afternoons", "data that arrives in three different formats",
    "the deadline at the end of next month", "the need for it to run without a babysitter",
    "the way you describe the current workaround", "the fact that nobody on your team owns this today",
    "your point that accuracy matters more than speed", "the requirement that it stays inside your existing stack",
    "the part about handing it over cleanly", "the first milestone you describe",
]
HOOK2 = [
    "You list {skill} in your requirements, and that is what I use most days. {Detail} is where I would begin.",
    "Your post mentions {skill}. I have shipped it in production more than once, and {detail} is what I would check first.",
]
EXPERIENCE_ROLES = {
    "ai_ml": ["Machine Learning Engineer", "Data Scientist", "Junior ML Engineer"],
    "fullstack": ["Full-Stack Developer", "Web Developer", "Junior Software Engineer"],
    "data_analyst": ["Senior Data Analyst", "Business Analyst", "Reporting Analyst"],
}
COMPANIES = ["Arbor Systems", "Delta Quarry", "BlueSail Technologies", "Kestrel Digital", "Paragon Analytics", "Tandem Labs",
             "Lanternworks", "Orbit Commerce"]
VAGUE_READMES = [
    "# {slug}\n\nweekend experiment, nothing polished. Some scripts I use.\n\nProbably broken on a fresh machine.\n",
    "# {slug}\n\nUtility scripts I keep around for client work. No docs, sorry.\n",
    "# {slug}\n\nScratch space for a small job. Read the code, it is short.\n\nTODO: tidy up.\n",
    "# {slug}\n\nmisc scripts, will clean up later\n",
    "# {slug}\n\nNotes and scripts from a side project. Not production-ready.\n",
    "# {slug}\n\nPersonal sandbox. Things in here change without warning.\n",
]
STOP = {"for", "a", "an", "the", "of", "to", "on", "with", "and", "in", "at"}
VAGUE_SLUGS = ["weekend-experiments", "scratch-utils", "misc-scripts", "playground", "notes-and-tools", "utils-v2",
               "sandbox", "tinkering", "quick-scripts", "small-tools", "side-experiments", "scratchpad"]


# ------------------------------------------------------------------ helpers
def _fmt_metric(rng, kind, noun):
    if kind == "time":
        a, b = pick(rng, [("4 days", "6 hours"), ("3 days", "5 hours"), ("two working days", "40 minutes"),
                          ("6 hours", "25 minutes"), ("a full week", "a single afternoon"), ("90 minutes", "8 minutes"),
                          ("11 days", "2 days"), ("5 hours", "20 minutes"), ("half a day", "15 minutes")])
        return dict(kind=kind, noun=noun, a=a, b=b, pct=0)
    if kind == "accuracy":
        a = rng.randint(60, 84)
        b = min(97, a + rng.randint(6, 18))
        return dict(kind=kind, noun=noun, a=f"{a}%", b=f"{b}%", pct=b - a)
    if kind == "cost":
        return dict(kind=kind, noun=noun, a="", b="", pct=rng.randint(12, 48))
    if kind == "revenue":
        if any(w in noun for w in ("rate", "retention", "share", "conversion")):
            a = round(rng.uniform(1.6, 38.0), 1)
            b = round(a * rng.uniform(1.12, 1.45), 1)
            return dict(kind=kind, noun=noun, a=f"{a}%", b=f"{b}%", pct=int((b / a - 1) * 100))
        a = rng.randint(18, 90)
        b = int(a * rng.uniform(1.12, 1.5))
        return dict(kind=kind, noun=noun, a=f"${a}k a month", b=f"${b}k a month", pct=int((b / a - 1) * 100))
    if kind == "volume":
        return dict(kind=kind, noun=noun, a="", b="", pct=rng.randint(35, 88))
    return dict(kind=kind, noun=noun, a="", b="", pct=rng.randint(30, 80))


def metric_text(rng, m, voice):
    d = TB.MET[m["kind"]]
    t = pick(rng, d[voice])
    return t.format(noun=m["noun"], Noun=cap(m["noun"]), a=m["a"], A=cap(m["a"]), b=m["b"], pct=m["pct"], Pct=m["pct"])


def _pairs_text(skills):
    return join_and(skills)


class Persona:
    pass


def _client_names(rng, industries, n):
    used = set()
    out = []
    firsts = TB.CLIENT_FIRST[:]
    rng.shuffle(firsts)
    for i in range(n):
        ind = TB.INDUSTRIES[industries[i]]
        name = f"{firsts[i]} {pick(rng, ind['suffix'])}"
        if chance(rng, 0.25):
            name += pick(rng, [" Ltd", " Inc", " Group", " Co"])
        out.append(name)
    return out


def build_projects(pid, rng):
    prof = PROFILES[pid]
    specs = PROJECT_SPECS[pid]
    inds = [s[1] for s in specs]
    names = _client_names(rng, inds, len(specs))
    projects = []
    scale = {"ai_ml": 1.0, "fullstack": 0.85, "data_analyst": 0.5}[pid]
    for i, (title, ind, need, named, implied, mk, mn, cat) in enumerate(specs, 1):
        d = rand_date(rng, dt.date(2022, 4, 1), dt.date(2026, 7, 28))
        eng = weighted(rng, [("fixed", 62), ("hourly", 38)])
        if eng == "fixed":
            price = int(round(rng.uniform(700, 5200) * scale / 50.0) * 50)
        else:
            price = int(round(rng.randint(30, 180) * prof["hourly_rate_usd"] * rng.uniform(0.9, 1.1) / 10.0) * 10)
        skills = sorted(set(named) | set(implied))
        indd = TB.INDUSTRIES[ind]
        projects.append(dict(
            project_id=f"{pid}-p{i:02d}", title=title, industry=ind, industry_label=indd["label"],
            client_name=names[i - 1], date=d, engagement=eng, price_usd=price, need=need, named=list(named),
            implied=list(implied), skills=skills, category=cat, metric=_fmt_metric(rng, mk, mn),
            ent=indd["ent"], Ent=cap(indd["ent"]), table=indd["table"], weeks=rng.randint(3, 14)))
    return projects


# ---------------------------------------------------------------- case studies
def _skill_sentences(rng, proj):
    items = [(s, "named") for s in proj["named"]] + [(s, "implied") for s in proj["implied"]]
    rng.shuffle(items)
    reasons = REASONS[:]
    rng.shuffle(reasons)
    sents = []
    for s, mode in items:
        np_ = pick(rng, BASE[s]["implied_by"])
        if mode == "implied":
            t = pick(rng, TB.IMPLIED_USE)
            sent = t.format(np=np_, Np=cap(np_))
        elif BASE[s]["category"] == "language":
            sent = pick(rng, LANG_USE).format(name=s, Name=s)
        else:
            ch = [t for t in TB.NAMED_USE if not (t.startswith("{Name}") and s[0].islower())]
            sent = pick(rng, ch).format(name=s, Name=s, np=np_)
        if reasons and chance(rng, 0.6):
            sent += " " + reasons.pop()
        if reasons and chance(rng, 0.2):
            sent += " " + reasons.pop()
        sents.append(sent)
    return sents


def _paragraphs_from(rng, sents):
    paras = []
    i = 0
    trans_pool = [t for t in TB.TRANS if t]
    rng.shuffle(trans_pool)
    while i < len(sents):
        k = rng.randint(2, 3)
        chunk = sents[i:i + k]
        i += k
        if chunk and chance(rng, 0.6):
            first = chunk[0]
            tr = trans_pool.pop() if trans_pool else ""
            fw = first.split()[0]
            if tr and fw in ("The", "Along", "A", "We", "To", "There", "Behind", "Later", "What", "Part", "Using", "On", "For"):
                chunk[0] = tr + first[0].lower() + first[1:]
            elif tr and fw == "I":
                chunk[0] = tr + first
        paras.append(" ".join(chunk))
    return paras


def case_study_text(rng, persona, proj):
    prof = persona["profile"]
    metric = proj["metric"]
    client = proj["client_name"]
    contact = pick(rng, TB.CONTACTS)
    ctx = dict(client=client, Client=client, need=proj["need"], ind=proj["industry_label"], a_ind=a_an(proj["industry_label"]),
               monthyear=f"{dt.date(proj['date'].year, proj['date'].month, 1):%B %Y}", quote=pick(rng, TB.QUOTES),
               contact=contact, Contact=cap(contact), role=prof["role"], n=rng.randint(4, 12),
               weeks=proj["weeks"], engagement=proj["engagement"])
    nf = metric_text(rng, metric, "nf")
    ctx["Nf"] = cap(nf)
    opener = pick(rng, TB.OPENERS).format(**ctx)
    sents = _skill_sentences(rng, proj)
    approach = _paragraphs_from(rng, sents)
    res_p = metric_text(rng, metric, "cs")
    if chance(rng, 0.6):
        res_p += " " + pick(rng, OUTCOMES_EXTRA).format(team=pick(rng, TEAM), contact=contact, Contact=cap(contact),
                                                         client=client)
    w1 = max(1, proj["weeks"] // 4)
    ctx_pool = rng.sample(TB.CHALLENGES, 2) + [pick(rng, DATA_NOTES)]
    rng.shuffle(ctx_pool)
    proc_pool = [pick(rng, TB.COLLAB).format(contact=contact, Contact=cap(contact)),
                 pick(rng, TIMELINES).format(w1=w1, w2=w1 + 1, w3=max(w1 + 2, proj["weeks"] - 1)),
                 pick(rng, SCOPE).format(contact=contact), pick(rng, TESTING), pick(rng, RISKS)]
    rng.shuffle(proc_pool)
    after_pool = [pick(rng, POSTLAUNCH), pick(rng, TB.LESSONS), pick(rng, TB.HANDOFF)]
    rng.shuffle(after_pool)
    target = rng.randint(330, 650)
    stack_line = join_and(proj["named"])
    structure = rng.randrange(5)
    heads = pick(rng, TB.HEAD_SETS)
    plan = [(1, 1, 1), (2, 1, 1), (2, 2, 1), (2, 2, 2), (2, 3, 2), (2, 4, 2), (3, 4, 2), (3, 5, 3)]
    chosen = 0
    body = ""
    for k, (a, b, c) in enumerate(plan):
        body = _assemble(structure, heads, opener, ctx_pool[:a], approach, proc_pool[:b], stack_line, res_p, after_pool[:c])
        chosen = k
        if nwords(body) >= target:
            break
    while nwords(body) > 700 and chosen > 0:
        chosen -= 1
        a, b, c = plan[chosen]
        body = _assemble(structure, heads, opener, ctx_pool[:a], approach, proc_pool[:b], stack_line, res_p, after_pool[:c])
    if nwords(body) < 255:
        body += "\n\n" + pick(rng, [
            "In short: a small, dependable system the team could own after I left, measured against numbers we agreed in week one.",
            "I would take the same approach again: agree the measure, ship a thin slice early and keep the design boring enough to hand over."])
    return body


def _assemble(structure, heads, opener, ctxs, approach, procs, stack_line, res_p, afters):
    sep = chr(10) * 2
    cj = sep.join(ctxs)
    if structure == 0:  # headed sections
        parts = [opener, f"## {heads[0]}{sep}{cj}", f"## {heads[1]}{sep}" + sep.join(approach + procs),
                 f"## {heads[2]}{sep}{stack_line}.", f"## {heads[3]}{sep}" + sep.join([res_p] + afters)]
    elif structure == 1:  # narrative
        parts = [opener] + ctxs + approach + [f"The tools involved were {stack_line}."] + procs + [res_p] + afters
    elif structure == 2:  # bold labels
        parts = [opener, f"**Situation.** {cj}", "**Approach.** " + sep.join(approach + procs), f"**Stack:** {stack_line}",
                 f"**Result.** {res_p}"] + afters
    elif structure == 3:  # result first
        parts = [opener, f"### What happened{sep}{res_p}", f"### How{sep}" + sep.join(approach + procs),
                 f"### Constraints{sep}{cj}"] + afters + [f"Tools: {stack_line}."]
    else:  # bullets
        bl = chr(10).join(f"- {x}" for x in approach)
        parts = [opener, cj, f"Key decisions:{sep}{bl}"] + procs + [f"Stack: {stack_line}.", f"Results: {res_p}"] + afters
    return sep.join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------------- repos
LANG_PREF = {"ai_ml": ["py", "docker"], "fullstack": ["ts", "tsx", "js", "yaml", "sql", "json", "prisma", "css", "liquid", "sh", "docker"],
             "data_analyst": ["sql", "py", "yaml", "dax", "lkml", "js"]}
EXT = {"py": "py", "sql": "sql", "ts": "ts", "tsx": "tsx", "js": "js", "yaml": "yml", "docker": "", "json": "json",
       "prisma": "prisma", "css": "css", "liquid": "liquid", "sh": "sh", "dax": "dax", "lkml": "lkml"}
COMMENT = {"py": "#", "sh": "#", "yaml": "#", "docker": "#", "lkml": "#", "ts": "//", "tsx": "//", "js": "//",
           "prisma": "//", "dax": "//", "sql": "--", "css": "/*", "liquid": "{% comment %}"}


def _variants(skill, persona_id, project_skills):
    vs = [v for v in CS.S.get(skill, []) if set(v["reveals"]) <= (project_skills | CS.BASE_LANG_SKILLS)
          and (v.get("for_") is None or persona_id in v["for_"])]
    if not vs:
        return []
    if skill in ("dbt", "Django"):
        return vs
    pref = LANG_PREF[persona_id]
    for lang in pref:
        sel = [v for v in vs if v["lang"] == lang]
        if sel:
            return sel[:1]
    return vs[:1]


def _replace_tokens(text, proj):
    return text.replace("@Ent@", proj["Ent"]).replace("@ent@", proj["ent"]).replace("@table@", proj["table"])


def _pad(rng, lang, lines, need):
    cm = COMMENT.get(lang)
    if cm is None or lang == "json" or len(lines) >= need:
        return lines
    notes = CS.PAD_NOTES[:]
    rng.shuffle(notes)
    block = notes[:min(18, max(0, need - len(lines) - 1))]
    if lang == "css":
        add = ["/* " + x + " */" for x in block]
    elif lang == "liquid":
        add = ["{% comment %} " + x + " {% endcomment %}" for x in block]
    else:
        add = [f"{cm} {x}" for x in block]
    if lang == "sh":
        return lines[:1] + add + lines[1:]
    return add + [""] + lines if lang not in ("yaml", "docker") else add + lines


NEUTRAL = {"py": ["helpers.py", "pipeline.py", "core.py", "main.py", "utils.py"],
           "ts": ["index.ts", "lib.ts", "services.ts", "core.ts"], "tsx": ["App.tsx", "views.tsx", "ui.tsx"],
           "js": ["index.js", "lib.js", "main.js"], "sql": ["analysis.sql", "reports.sql", "views.sql"]}


def _bin_pack(rng, chosen, proj):
    """group snippet variants into 2-4 files; merge same-language snippets until a file is ~30 lines."""
    def pack(merge):
        files = []
        for v in chosen:
            n = len(v["body"].split("\n")) + len(v["imports"])
            placed = False
            if merge and v["lang"] in ("py", "ts", "tsx", "js", "sql"):
                for f in files:
                    if f["lang"] == v["lang"] and f["n"] < 30 and f["n"] + n <= 96:
                        f["vs"].append(v)
                        f["n"] += n
                        placed = True
                        break
            if not placed:
                name = _replace_tokens(v["file"], proj)
                if name.startswith("src/"):
                    name = name[4:]
                if any(f["name"] == name for f in files):
                    continue
                files.append(dict(lang=v["lang"], name=name, vs=[v], n=n))
        return files
    files = pack(True)
    if len(files) < 2 and len(chosen) >= 2:
        files = pack(False)
    used = {f["name"] for f in files}
    for f in files:
        if len(f["vs"]) > 1 and f["lang"] in NEUTRAL:
            opts = [n for n in NEUTRAL[f["lang"]] if n not in used]
            if opts:
                used.discard(f["name"])
                f["name"] = pick(rng, opts)
                used.add(f["name"])
    while len(files) > 4:
        files.pop()
    return files


def build_repo_files(rng, persona_id, proj, skills_for_repo):
    """returns (files dict path->text, revealed skills set, languages list)"""
    pskills = set(proj["skills"])
    chosen = []
    for s in skills_for_repo:
        chosen.extend(_variants(s, persona_id, pskills))
    packed = _bin_pack(rng, chosen, proj)
    files = {}
    revealed = set()
    langs = []
    for pf in packed:
        fname, lang, vs = pf["name"], pf["lang"], pf["vs"]
        imports = []
        for v in vs:
            for im in v["imports"]:
                im = _replace_tokens(im, proj)
                if im not in imports:
                    imports.append(im)
        bodies = [_replace_tokens(v["body"], proj) for v in vs]
        for v in vs:
            revealed.update(v["reveals"])
        lines = []
        is_test = any(t in fname for t in ("test", "spec", ".cy."))
        if lang == "py":
            fillers = []
            fl = CS.FILLER_PY[:]
            rng.shuffle(fl)
            est = sum(len(b_.split("\n")) + 2 for b_ in bodies) + len(imports) + 4
            for fi, fb in fl:
                if est >= 34:
                    break
                fillers.append((fi, fb))
                est += len(fb.strip("\n").split("\n")) + 2
            for fi, fb in fillers:
                for im in fi.split("\n"):
                    if im and im not in imports:
                        imports.append(im)
            if chance(rng, 0.5):
                lines += ['"""' + f"{proj['title']}: {fname.split('/')[-1].replace('.py', '').replace('_', ' ')} helpers." + '"""', ""]
            std_mods = ("os", "re", "json", "math", "csv", "time", "random", "statistics", "subprocess", "sys", "logging",
                        "typing", "collections", "datetime", "pathlib")
            std = [i for i in imports if i.split()[1].split(".")[0] in std_mods]
            third = [i for i in imports if i not in std]
            lines += sorted(std) + ([""] if std and third else []) + sorted(third)
            lines += ["", ""]
            for b_ in bodies:
                lines += b_.split("\n") + ["", ""]
            for fi, fb in fillers:
                lines += fb.strip("\n").split("\n") + ["", ""]
        elif lang in ("ts", "tsx", "js"):
            lines += imports + ([""] if imports else [])
            for b_ in bodies:
                lines += b_.split("\n") + [""]
            fl = CS.FILLER_TS[:]
            rng.shuffle(fl)
            while len(lines) < 34 and fl and lang != "js" and not is_test:
                lines += fl.pop().strip("\n").split("\n") + [""]
        else:
            for b_ in bodies:
                lines += b_.split("\n") + [""]
        while lines and lines[-1] == "":
            lines.pop()
        lines = _pad(rng, lang, lines, 32)
        if len(lines) > 118:
            lines = lines[:118]
        out_name = fname
        lang_eff = lang
        if lang in ("ts", "tsx") and "TypeScript" not in pskills:
            out_name = fname.rsplit(".", 1)[0] + (".jsx" if lang == "tsx" else ".js")
            lang_eff = "js"
        files[out_name] = "\n".join(lines) + "\n"
        langs.append(lang_eff)
        implicit = {"py": "Python", "sql": "SQL", "ts": "TypeScript", "tsx": "TypeScript", "js": "JavaScript"}.get(lang_eff)
        if implicit and implicit in pskills:
            revealed.add(implicit)
    return files, revealed & pskills, langs


def usable_snippet_skills(persona_id, proj):
    pskills = set(proj["skills"])
    return [s for s in proj["skills"] if _variants(s, persona_id, pskills)]


def _readme_informative(rng, proj, stack_names, files):
    title = proj["title"]
    ai = a_an(proj["industry_label"])
    one = pick(rng, [
        f"Small service built for {ai} team that needed to {proj['need']}.",
        f"Internal tooling from {ai} engagement. Goal: {proj['need']}.",
        f"Code behind {ai} project. The aim was to {proj['need']}.",
    ])
    first = sorted(files)[0]
    run = "npm install\nnpm run dev" if first.endswith((".ts", ".tsx", ".js", ".jsx")) else (
        "pip install -r requirements.txt\npython " + first if first.endswith(".py") else "See the files under src/ in order.")
    style = rng.randrange(3)
    if style == 0:
        return (f"# {title}\n\n{one}\n\n## Stack\n\n" + "\n".join(f"- {s}" for s in stack_names) +
                f"\n\n## Getting started\n\n```\n{run}\n```\n\n## Layout\n\n" +
                "\n".join(f"- `src/{f}`" for f in sorted(files)) + "\n")
    if style == 1:
        return (f"# {title}\n\n{one}\n\nBuilt with {join_and(stack_names)}.\n\n### Run\n\n```\n{run}\n```\n\n"
                "### Notes\n\nConfig lives in environment variables. See `.env.example` (not committed).\n")
    return (f"{title}\n{'=' * len(title)}\n\n{one}\n\nTech: {', '.join(stack_names)}\n\nStatus: delivered, "
            f"handed over to the client in {proj['date']:%B %Y}.\n")


def build_repos(pid, rng, projects, n_target):
    cand = []
    for p in projects:
        us = usable_snippet_skills(pid, p)
        if len(us) >= 2:
            cand.append((p, us))
    rng.shuffle(cand)
    cand = cand[:n_target]
    cand.sort(key=lambda x: x[0]["project_id"])
    n_vague = max(2, round(len(cand) / 3))
    vague_idx = set(rng.sample(range(len(cand)), n_vague))
    used_slugs = set()
    vague_slugs = VAGUE_SLUGS[:]
    rng.shuffle(vague_slugs)
    repos = []
    for i, (p, us) in enumerate(cand, 1):
        k = min(len(us), rng.randint(3, 5))
        sel = pick_n(rng, us, k)
        files, revealed, langs = build_repo_files(rng, pid, p, sel)
        if len(files) < 2:  # add one more skill to reach two files
            rest = [s for s in us if s not in sel]
            for s in rest:
                files, revealed, langs = build_repo_files(rng, pid, p, sel + [s])
                if len(files) >= 2:
                    break
        vague = (i - 1) in vague_idx
        if vague:
            slug = vague_slugs.pop()
            readme = pick(rng, VAGUE_READMES).format(slug=slug)
            skills = set(revealed)
        else:
            sw = [w for w in slugify(p["title"]).split("-") if w not in STOP]
            slug = "-".join(sw[:3])
            slug = slug if slug not in used_slugs else slug + "-svc"
            named_pool = [s for s in p["named"] if s in (revealed | set(p["named"]))]
            stack_names = pick_n(rng, list(dict.fromkeys(sorted(revealed & set(p["named"])) + named_pool)), min(4, len(named_pool)))
            if not stack_names:
                stack_names = pick_n(rng, p["named"], 2)
            readme = _readme_informative(rng, p, stack_names, files)
            skills = set(revealed) | set(stack_names)
        used_slugs.add(slug)
        cnt = collections.Counter(l for l in langs if l in ("py", "ts", "tsx", "js", "sql"))
        cnt["ts"] += cnt.pop("tsx", 0)
        order = ["py", "ts", "js", "sql"]
        top = max(order, key=lambda l: (cnt.get(l, 0), -order.index(l))) if cnt else "py"
        language = {"py": "Python", "ts": "TypeScript", "js": "JavaScript", "sql": "SQL"}[top]
        d = p["date"] + dt.timedelta(days=rng.randint(-20, 40))
        d = min(d, dt.date(2026, 9, 30))
        repos.append(dict(item_id=f"{pid}-repo-{i:02d}", project_id=p["project_id"], slug=slug, date=month_str(d),
                          language=language, readme=readme, files=files, skills=sorted(skills), vague=vague))
    return repos


# -------------------------------------------------------------------- reviews
def build_reviews(pid, rng, projects):
    prof = PROFILES[pid]
    first = prof["name"].split()[0]
    n = rng.randint(12, 18)
    chosen = [rng.choice(projects) for _ in range(n)]
    reviews = []
    ratings = [weighted(rng, [(5, 52), (4, 26), (3, 13), (2, 9)]) for _ in chosen]
    for need_r in (2, 3):
        if need_r not in ratings:
            ratings[rng.randrange(len(ratings))] = need_r
    if 5 not in ratings:
        ratings[rng.randrange(len(ratings))] = 5
    for i, p in enumerate(chosen, 1):
        rating = ratings[i - 1]
        parts = [pick(rng, TB.REV_OPEN[rating]).format(first=first)]
        k = 1 if rating <= 3 else rng.randint(1, 2)
        skl = pick_n(rng, p["skills"], k)
        expressed = []
        for s in skl:
            np_ = pick(rng, BASE[s]["implied_by"])
            parts.append(pick(rng, TB.REV_SKILL).format(np=np_, first=first))
            expressed.append(s)
        if rating >= 3 and chance(rng, 0.55):
            parts.append(cap(metric_text(rng, p["metric"], "rev")) + ".")
        end = pick(rng, TB.REV_END if rating >= 4 else TB.REV_END_LOW).format(first=first)
        if end:
            parts.append(end)
        d = min(p["date"] + dt.timedelta(days=rng.randint(10, 80)), dt.date(2026, 10, 20))
        reviews.append(dict(item_id=f"{pid}-rev-{i:02d}", project_id=p["project_id"], client_industry=p["industry_label"],
                            rating=rating, date=d.isoformat(), text=" ".join(parts), skills=sorted(set(expressed))))
    return reviews


# ------------------------------------------------------------------- proposals
def _fair_bid(rng, category, n_skills, hourly, rate):
    base, hbase = AR.CATEGORY_PRICE.get(category, (1000, 40))
    if hourly:
        return int(round(rate * rng.uniform(0.85, 1.25)))
    return int(round(base * AR.CX_FACTOR[AR.complexity_bucket(n_skills)] * rng.uniform(0.6, 1.4) / 10.0) * 10)


def _evidence(rng, proj, include_numbers=True, n_named=3, intro_t=None):
    named = pick_n(rng, proj["named"], min(n_named, len(proj["named"])))
    expressed = list(named)
    parts = [(intro_t or pick(rng, TB.EVID_INTRO)).format(ind=proj["industry_label"], a_ind=a_an(proj["industry_label"]), need=proj["need"])]
    parts.append(f"The stack was {join_and(named)}.")
    if proj["implied"] and chance(rng, 0.6):
        s = pick(rng, proj["implied"])
        parts.append(f"It also involved {pick(rng, BASE[s]['implied_by'])}.")
        expressed.append(s)
    if include_numbers:
        parts.append(pick(rng, TB.EVID_RESULT).format(prop=metric_text(rng, proj["metric"], "prop")))
    return " ".join(parts), expressed


def build_proposals(pid, rng, projects, repos, n=150):
    prof = PROFILES[pid]
    archs = AR.archetypes_for(pid)
    props = []
    proj_by_cat = {}
    for p in projects:
        proj_by_cat.setdefault(p["category"], []).append(p)
    github_slugs = [r["slug"] for r in repos if not r["slug"] in VAGUE_SLUGS]
    for i in range(1, n + 1):
        a = pick(rng, archs)
        category = a["category"]
        k = rng.randint(2, 5)
        reqs = a["pool"][:2] + pick_n(rng, a["pool"][2:], max(0, k - 2))
        reqs = [r for r in dict.fromkeys(reqs)]
        title = pick(rng, a["titles"])
        task = pick(rng, a["tasks"])
        ind_key = pick(rng, sorted(TB.INDUSTRIES))
        ind = TB.INDUSTRIES[ind_key]["label"]
        hourly = chance(rng, 0.28)
        bid = _fair_bid(rng, category, len(reqs), hourly, prof["hourly_rate_usd"])
        d = rand_date(rng, dt.date(2022, 9, 1), dt.date(2026, 10, 25))
        job_summary = (f"{cap(a_an(ind))} client wants to {task}. Skills mentioned: {join_and([r for r in reqs[:4]])}." +
                       (" Hourly contract." if hourly else " Fixed-price contract."))
        # candidate projects by overlap
        scored = sorted(projects, key=lambda p: (-(2 * len(set(p["skills"]) & set(reqs)) + (3 if p["category"] == category else 0)
                                                    + rng.random()),))
        # quality tier
        tier = weighted(rng, [("high", 30), ("mid", 25), ("low", 45)])
        hook = tier == "high" or (tier == "mid" and chance(rng, 0.25)) or (tier == "low" and chance(rng, 0.06))
        generic_open = (tier == "low" and chance(rng, 0.9)) or (tier == "mid" and chance(rng, 0.2))
        evidence_level = {"high": weighted(rng, [(2, 80), (1, 20)]), "mid": weighted(rng, [(1, 55), (0, 35), (2, 10)]),
                          "low": weighted(rng, [(0, 88), (1, 12)])}[tier]
        paras = []
        expressed = []
        cited = []
        detail = pick(rng, DETAILS)
        if hook:
            if chance(rng, 0.3):
                sk = pick(rng, [r for r in reqs])
                t = pick(rng, HOOK2).format(skill=sk, Detail=cap(detail), detail=detail)
                expressed.append(sk)
            else:
                t = pick(rng, TB.HOOK_OPEN).format(task=task, detail=detail, Detail=cap(detail))
            paras.append(t)
        elif generic_open:
            paras.append(pick(rng, TB.GENERIC_OPEN).format(role=prof["role"], field=prof["field"]))
        else:
            paras.append(pick(rng, TB.MID_OPEN).format(category=category))
        if evidence_level >= 1:
            ps = scored[:2] if evidence_level == 2 and chance(rng, 0.5) else scored[:1]
            intros = rng.sample(TB.EVID_INTRO, 2)
            for j, pr in enumerate(ps):
                txt, ex = _evidence(rng, pr, include_numbers=(evidence_level == 2 or j == 0 and chance(rng, 0.4)),
                                    n_named=3, intro_t=intros[j])
                paras.append(txt)
                expressed += ex
                cited.append(pr["project_id"])
        else:
            gs = pick_n(rng, reqs, min(3, len(reqs)))
            for _ in range(2 if chance(rng, 0.5) else 1):
                t = pick(rng, TB.GENERIC_BODY)
                paras.append(t.format(skills=join_and(gs)))
                if "{skills}" in t:
                    expressed += gs
        plan = (tier == "high" and chance(rng, 0.85)) or (tier == "mid" and chance(rng, 0.4)) or (tier == "low" and chance(rng, 0.04))
        if plan:
            paras.append(pick(rng, TB.PLAN).format(d1=rng.randint(4, 9), d2=rng.randint(7, 16), weeks=rng.randint(3, 8)))
        quest = (tier == "high" and chance(rng, 0.7)) or (tier == "mid" and chance(rng, 0.3)) or (tier == "low" and chance(rng, 0.03))
        if quest:
            paras.append(pick(rng, TB.QUESTIONS))
        if github_slugs and evidence_level >= 1 and chance(rng, 0.12):
            paras.append(f"Sample code: github.com/{slugify(prof['name'])}/{pick(rng, github_slugs)}")
        paras.append(pick(rng, TB.CLOSE) if tier != "low" else pick(rng, TB.GENERIC_CLOSE))
        text = "\n\n".join(paras)
        # outcome model
        score = (2.0 if hook else 0.0) + {0: 0.0, 1: 1.3, 2: 2.4}[evidence_level] - (2.0 if generic_open else 0.0)
        score += 0.6 if plan else 0.0
        score += 0.5 if quest else 0.0
        p_nonign = 1 / (1 + math.exp(-(OUT_A * score + OUT_B)))
        r = rng.random()
        if r < p_nonign:
            p_won = 1 / (1 + math.exp(-(OUT_C * score + OUT_D)))
            outcome = "won" if rng.random() < p_won else "replied"
        else:
            outcome = "ignored"
        props.append(dict(
            item_id=f"{pid}-prop-{i:03d}", job_title=title, job_category=category, job_summary=job_summary,
            client_industry=ind, date=d.isoformat(), bid_usd=bid, proposal_text=text, outcome=outcome,
            cited_project_ids=sorted(set(cited)), _expressed=sorted(set(expressed) & set(BASE)), _hourly=hourly,
            _reqs=reqs, _tier=tier, _score=score))
    return props


# ------------------------------------------------------------------------- CV
def build_cv(pid, rng, persona):
    prof = persona["profile"]
    projects = persona["projects"]
    years = {"ai_ml": 6, "fullstack": 7, "data_analyst": 5}[pid]
    lines = [f"# {prof['name']}", f"{prof['headline']}", f"{prof['location']} | {prof['email']} | timezone {prof['timezone']}", ""]
    top = persona["skill_list"][:]
    lines += ["## Summary", "",
              f"{prof['role'].capitalize()} with {years} years of experience delivering {prof['field']} for small and "
              f"mid-sized companies in fintech, healthcare, e-commerce, logistics and media. Comfortable owning a problem from "
              f"first conversation to handover. Works with {join_and(pick_n(rng, top, 6))}.", ""]
    lines += ["## Experience", ""]
    roles = EXPERIENCE_ROLES[pid]
    comp = pick_n(rng, COMPANIES, 3)
    spans = [(2022, 2026), (2020, 2022), (2018, 2020)]
    projs = projects[:]
    rng.shuffle(projs)
    for (role, c, (a, b)), chunk in zip(zip(roles, comp, spans), [projs[0:3], projs[3:5], projs[5:7]]):
        lines.append(f"### {role}, {c} ({a} - {'present' if b == 2026 else b})")
        for pr in chunk:
            nm = pick_n(rng, pr["named"], min(3, len(pr["named"])))
            lines.append(f"- {cap(pr['need'])} using {join_and(nm)}; {metric_text(rng, pr['metric'], 'prop')}.")
        lines.append("")
    lines += ["## Projects", ""]
    for pr in sorted(projects, key=lambda x: x["date"], reverse=True)[:8]:
        lines.append(f"- {pr['title']} ({pr['date'].year}, {pr['industry_label']}): {join_and(pr['named'])}")
    lines += ["", "## Education", "", f"- {prof['education']}", ""]
    groups = {}
    for s in persona["skill_list"]:
        groups.setdefault(BASE[s]["category"], []).append(s)
    lines += ["## Skills", ""]
    for g in sorted(groups):
        lines.append(f"- {g.replace('_', ' ').title()}: {', '.join(groups[g])}")
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------- top-level build
def build_persona(pid, seed):
    prof = dict(PROFILES[pid])
    rng = random.Random(f"{seed}:{pid}:core")
    P = {"pid": pid, "profile": prof}
    projects = build_projects(pid, rng)
    P["projects"] = projects
    skill_set = set()
    for p in projects:
        skill_set |= set(p["skills"])
    P["skills"] = skill_set
    P["skill_list"] = sorted(skill_set)
    prof["skills"] = P["skill_list"]
    # case studies: all but 5 projects
    no_cs = set(rng.sample(range(len(projects)), 5))
    cs = []
    n = 0
    for idx, p in enumerate(projects):
        if idx in no_cs:
            continue
        n += 1
        body = case_study_text(rng, P, p)
        cs.append(dict(item_id=f"{pid}-cs-{n:02d}", project_id=p["project_id"], title=p["title"], body=body, proj=p))
    P["case_studies"] = cs
    P["repos"] = build_repos(pid, rng, projects, rng.randint(9, 11))
    P["reviews"] = build_reviews(pid, rng, projects)
    P["proposals"] = build_proposals(pid, rng, projects, P["repos"], 150)
    P["cv_md"] = build_cv(pid, rng, P)
    # gold
    gp = {p["project_id"]: dict(title=p["title"], industry=p["industry_label"], skills=list(p["skills"])) for p in projects}
    gi = {}
    gi[f"{pid}-cv-01"] = dict(type="cv", project_id=None, skills=P["skill_list"])
    for c in cs:
        gi[c["item_id"]] = dict(type="case_study", project_id=c["project_id"], skills=list(c["proj"]["skills"]))
    for r in P["repos"]:
        gi[r["item_id"]] = dict(type="repo", project_id=r["project_id"], skills=list(r["skills"]))
    for r in P["reviews"]:
        gi[r["item_id"]] = dict(type="review", project_id=r["project_id"], skills=list(r["skills"]))
    for pr in P["proposals"]:
        gi[pr["item_id"]] = dict(type="proposal", project_id=pr["cited_project_ids"][0] if pr["cited_project_ids"] else None,
                                 skills=list(pr["_expressed"]))
    P["gold_projects"] = gp
    P["gold_items"] = gi
    return P


def case_study_md(P, c):
    p = c["proj"]
    fm = ["---", f"item_id: {c['item_id']}", f"project_id: {c['project_id']}", f"title: {json.dumps(p['title'])}",
          f"date: {month_str(p['date'])}", f"client_industry: {json.dumps(p['industry_label'])}",
          f"client_name: {json.dumps(p['client_name'])}", f"engagement: {p['engagement']}", f"price_usd: {p['price_usd']}", "---", ""]
    return "\n".join(fm) + f"# {p['title']}\n\n" + c["body"] + "\n"
