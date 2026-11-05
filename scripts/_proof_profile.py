"""The proof profile: a public-ready page built only from evidence that was checked against a public source.

build_model reads the workspace and keeps what may be shown. render turns it into one self-contained page.
leak_problems is the guard: it looks at what is about to be written and returns plain reasons not to write it.
Used by scripts/proof_profile.py. Standard library only.
"""
import datetime as dt
import glob
import html
import os
import re
import string
from urllib.parse import urlsplit

import _common as C
import _levels as L
import _public_link as PL

CHECKED = ("verified", "corroborated")
# Kinds that are about other people or the person's private plans, never a public claim.
PRIVATE_KINDS = ("network", "eligibility", "preference")
PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_proof_profile_page.html")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SOURCE_NAMES = {"github": "GitHub", "website": "Website", "certification": "Certificate", "publication": "Publication",
                "talk": "Talk", "app_store": "App store", "linkedin_profile": "LinkedIn profile",
                "web_search": "Public web", "other": "Source"}

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
PHONE = re.compile(r"(?<![\w/.:-])\+?\(?\d[\d\s().-]{7,}\d(?![\w-])")
HOME_PATH = re.compile(r"(?:/Users/|/home/)[^\s/\"'<>]+|[A-Za-z]:\\Users\\|(?<![\w.])~/")
URL = re.compile(r"(?:https?|file|ftp)://[^\s\"'<>)]+|file:/[^\s\"'<>)]+", re.I)
LOCAL_HOST = re.compile(r"(?<![\w.-])(?:localhost|127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
                        r"|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|[\w-]+\.(?:local|internal|lan))(?![\w-])", re.I)
CLAIM_LEVEL = re.compile(r'data-claim-level="([^"]*)"')


def nice_date(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year)


def level_rows(runs):
    """[{date, level, band, change, rules_changed}] from the scored runs, oldest first. A run's level is the
    band of its best fit across the judged roles."""
    pts = []
    for run in runs:
        fits = [r["fit"] for r in run.get("roles") or [] if isinstance(r.get("fit"), (int, float))]
        if fits:
            pts.append({"date": run["run_date"], "top": max(fits), "rubric_version": run.get("rubric_version")})
    return [{"date": r["date"], "level": r["level"], "band": r["band"], "change": r["change"],
             "rules_changed": r["not_comparable"]} for r in L.level_history(pts)]


def load_runs(ws):
    out = []
    for f in sorted(glob.glob(C.wpath(ws, "eval", "runs", "*.json"))):
        run = C.load_json(f)
        if run and (run.get("counts") or {}).get("judged", 1):
            out.append(run)
    return out


def events_by_date(ws):
    """Level events from eval/levels.json when workstream B has written them; none otherwise."""
    doc = C.load_json(C.wpath(ws, "eval", "levels.json"), None)
    events = doc.get("events") if isinstance(doc, dict) else None
    return {e["date"]: e["kind"] for e in events or [] if isinstance(e, dict) and e.get("date") and e.get("kind")}


def public_sources(item):
    return [s for s in item.get("sources") or [] if PL.source_is_public(s)]


def build_model(ws, config, today):
    """What the page will say. Claims are kept only when their level is verified or corroborated (after the
    public-link rule) and at least one source is a public https link the reader can open."""
    ev = (C.load_json(C.wpath(ws, "profile", "evidence.json"), {}) or {}).get("items") or []
    claims, held_back = [], 0
    for item in ev:
        if PL.effective_level(item) not in CHECKED or item.get("kind") in PRIVATE_KINDS:
            continue
        links = public_sources(item)
        if not links:
            held_back += 1
            continue
        claims.append({"id": item["id"], "claim": item["claim"], "level": PL.effective_level(item),
                       "sources": [{"url": s["ref"], "type": s["type"], "checked_on": s.get("checked_on")} for s in links]})
    runs = load_runs(ws)
    rows = level_rows(runs)
    marks = events_by_date(ws)
    for r in rows:
        r["event"] = marks.get(r["date"])
    goal = config.get("goal") or {}
    return {"name": (config.get("candidate") or {}).get("display_name") or "",
            "goal": {k: goal.get(k) for k in ("title", "role", "where", "by") if isinstance(goal.get(k), str) and goal.get(k)},
            "levels": rows, "claims": claims, "held_back": held_back, "built_on": today,
            "fictional": bool(config.get("fictional")),
            "redact_terms": [t for t in (config.get("privacy") or {}).get("redact_terms") or [] if t]}


# ------------------------------------------------------------------ render


def esc(text):
    return html.escape(text or "", quote=True)


def source_label(src):
    host = urlsplit(src["url"]).hostname or ""
    path = urlsplit(src["url"]).path.rstrip("/")
    return esc(host.replace("www.", "", 1) + path)


def claim_html(c):
    word = "Verified" if c["level"] == "verified" else "Corroborated"
    links = []
    for s in c["sources"]:
        when = " <span>(checked %s)</span>" % nice_date(s["checked_on"]) if s.get("checked_on") else ""
        links.append('%s: <a href="%s" rel="noopener">%s</a>%s' % (esc(SOURCE_NAMES.get(s["type"], "Source")),
                                                                  esc(s["url"]), source_label(s), when))
    return ('<li class="claim" data-claim-level="%s"><p><span class="badge">%s</span>%s</p>\n<p class="src">%s</p></li>'
            % (c["level"], word, esc(c["claim"]), "<br>".join(links)))


def history_html(rows):
    if not rows:
        return '<p class="note">No scored runs yet.</p>'
    items = []
    for r in reversed(rows):
        tags = ""
        if r["event"] == "goal_reached":
            tags += '<span class="tag">Goal reached</span>'
        if r["change"] == "up":
            tags += '<span class="tag">Level up</span>'
        if r["rules_changed"]:
            tags += '<span class="tag">Scoring rules updated</span>'
        items.append('<li><span>Level %d, %s%s</span><span class="when">%s</span></li>'
                     % (r["level"], esc(r["band"]), tags, nice_date(r["date"])))
    return '<ol class="hist">\n%s\n</ol>' % "\n".join(items)


def render(model):
    rows, cur = model["levels"], (model["levels"] or [None])[-1]
    g = model["goal"]
    meta = [x for x in (g.get("role"), g.get("where"), ("by " + nice_date(g["by"])) if re.match(r"\d{4}-\d\d-\d\d$", g.get("by", "")) else None) if x]
    name = model["name"] or "Proof profile"
    cl = model["claims"]
    if cl:
        claims = '<ul class="claims">\n%s\n</ul>' % "\n".join(claim_html(c) for c in cl)
    else:
        claims = '<p class="note">No claims have been checked against a public source yet.</p>'
    footer = ("Only claims checked against a public source are shown. Everything else is left out"
              + (", including %d checked claim%s with no public link." % (model["held_back"], "" if model["held_back"] == 1 else "s")
                 if model["held_back"] else "."))
    values = {
        "title": esc("%s: proof profile" % name),
        "description": esc("%s. %d checked claims, each with its source." % (g.get("title") or name, len(cl))),
        "banner": '<p class="demo">This is a fictional demo profile. Alex Example is not a real person.</p>' if model["fictional"] else "",
        "name": esc(name), "goal": esc(g.get("title") or "Goal not set yet"),
        "goal_meta": '<p class="goal-meta">%s</p>' % esc(", ".join(meta)) if meta else "",
        "level": cur["level"] if cur else 0, "band": esc(cur["band"]) if cur else "No",
        "level_date": nice_date(cur["date"]) if cur else "no scored run yet",
        "segs": "".join('<i class="on"></i>' if cur and i < cur["level"] else "<i></i>" for i in range(5)),
        "level_note": "Levels run from 1 (Very low) to 5 (Strong) and come from scored runs on evidence, not from opinion."
                      if cur else "Levels appear after the first scored run.",
        "history": history_html(rows), "claims": claims, "footer": esc(footer),
        "built": nice_date(model["built_on"]),
    }
    with open(PAGE, encoding="utf-8") as fh:
        return string.Template(fh.read()).substitute(values)


# ------------------------------------------------------------------ the leak check


def visible_text(page):
    page = re.sub(r"<(style|script)\b.*?</\1>", " ", page, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", page))


def leak_problems(page, redact_terms=()):
    """Plain reasons the page must not be written; an empty list means it is clean."""
    out, text = [], visible_text(page)
    hrefs = [html.unescape(h) for h in re.findall(r'href="([^"]*)"', page)]
    if EMAIL.search(text) or any(EMAIL.search(h) or h.lower().startswith("mailto:") for h in hrefs):
        out.append("it would contain an email address")
    if any(len(re.sub(r"\D", "", m)) >= 9 and not re.fullmatch(r"\d{4}-\d\d-\d\d", m.strip()) for m in PHONE.findall(text)):
        out.append("it would contain a phone number")
    if HOME_PATH.search(text) or any(HOME_PATH.search(h) for h in hrefs):
        out.append("it would contain a folder path from your computer")
    urls = URL.findall(text) + hrefs + re.findall(r'(?:src|action)="([^"]*)"', page)
    if any(u and not PL.is_public_link(u) for u in urls) or LOCAL_HOST.search(text):
        out.append("it would contain a private-network, local or non-https link")
    if re.search(r"<(script|link|iframe|img|form)\b|@import|url\(", page, re.I):
        out.append("it would ask the reader's browser to load something from outside the page")
    low = [m for m in CLAIM_LEVEL.findall(page) if m not in CHECKED]
    if low:
        out.append("it would contain a claim below corroborated (%s)" % ", ".join(sorted(set(low))))
    for term in redact_terms:
        if term.lower() in text.lower():
            out.append("it would contain a name you asked to keep out of anything shared (%s)" % term)
    return out
