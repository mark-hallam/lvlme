"""Interview story bank (profile/stories.json): the person's best true stories, ready for interviews.

Interviews ask about past behaviour, and the usual shape for an answer is STAR:
situation, task, action, result (plus what you would do differently). Each
story is in the person's own words, links to the evidence behind it, and names
the question themes it answers. Its strength is the best evidence level among
its evidence ids. It is backed when that is verified or corroborated; a story
with no evidence, or only the person's word or partly checked evidence, is
"not backed yet".

THEMES are inferred from common interview guidance: no employer publishes its
question list. config.json can replace them (stories.themes). A theme with no
story, or no story backed by evidence, is a gap, and a gap can become a
plan action (scripts/stories.py plan).

Never invent a story or a number (hard rule 2). Progress only: score.py never
reads this file. No network calls here.
"""
import html
import re

REL = "profile/stories.json"
THEMES = [
    {"id": "why_here", "name": "Why this organisation", "ask": "Why do you want to work here, on this mission?"},
    {"id": "impact", "name": "Impact with a number", "ask": "Tell me about something you changed that you can measure."},
    {"id": "hard_problem", "name": "A hard problem solved", "ask": "Tell me about the hardest problem you have solved."},
    {"id": "mistake", "name": "A mistake and what changed", "ask": "Tell me about a mistake, and what you changed after."},
    {"id": "disagree", "name": "Disagreeing well", "ask": "Tell me about a time you disagreed with a decision."},
    {"id": "lead", "name": "Leading without authority", "ask": "Tell me about getting people to act when they did not report to you."},
    {"id": "values", "name": "Values under pressure", "ask": "Tell me about a time doing the right thing cost you something."},
]
THEMES_NOTE = "Inferred from common interview guidance; no employer publishes its question list."
SOURCES = ["intake", "person", "debrief", "career-ops"]
STRONG = ("verified", "corroborated")
LEVEL_ORDER = ["verified", "corroborated", "partially_verified", "self_reported", "unverified", "contradicted"]
STATUS_NAMES = {"backed": "Backed by evidence", "practise": "Practise this", "word": "Not backed yet",
                "missing": "No story yet"}
NOTE = "Progress only: it changes no score. Every story is yours, in your words; LVLme never writes one for you."


def themes(config):
    return ((config or {}).get("stories") or {}).get("themes") or THEMES


def empty():
    return {"schema_version": 1, "stories": []}


def next_id(doc):
    n = max([int(s["id"][1:]) for s in (doc or {}).get("stories") or [] if re.match(r"^S\d+$", s.get("id", ""))] or [0])
    return "S%02d" % (n + 1)


def strength(story, levels):
    """The best evidence level behind a story, or self_reported when it has none."""
    found = [levels[e] for e in story.get("evidence") or [] if e in levels and levels[e] != "contradicted"]
    return min(found, key=LEVEL_ORDER.index) if found else "self_reported"


def levels_of(evidence_doc):
    return {e["id"]: e.get("level") for e in (evidence_doc or {}).get("items") or [] if e.get("id")}


def coverage(doc, config, evidence_doc, struggled=None):
    """One row per theme: status backed, practise (backed, but a real interview found it hard), word or missing,
    and the stories that answer it. struggled: {theme: real-interview gaps} (scripts/_practice.py)."""
    levels, stories, struggled = levels_of(evidence_doc), (doc or {}).get("stories") or [], struggled or {}
    out = []
    for t in themes(config):
        mine = [s for s in stories if t["id"] in (s.get("themes") or [])]
        strong = [s for s in mine if strength(s, levels) in STRONG]
        status = ("practise" if struggled.get(t["id"]) else "backed") if strong else "word" if mine else "missing"
        out.append({"id": t["id"], "name": t["name"], "ask": t.get("ask", ""), "status": status,
                    "stories": [s["id"] for s in mine], "struggled": struggled.get(t["id"], 0)})
    return out


def gaps(doc, config, evidence_doc, struggled=None):
    return [r for r in coverage(doc, config, evidence_doc, struggled) if r["status"] != "backed"]


def action_for(theme_row, plan, config, today):
    """A plan action for one story gap: D7 (application readiness), every target."""
    weight = ((config.get("scoring") or {}).get("weights") or {}).get("D7") or 5
    n = max([int(a["id"][1:]) for a in (plan or {}).get("actions") or [] if re.match(r"^A\d+$", a.get("id", ""))]
            or [0]) + 1
    missing = theme_row["status"] == "missing"
    return {"id": "A%02d" % n, "status": "todo", "owner": "you", "dimension": "D7", "orgs": "all",
            "title": ("Write a story for \"%s\"" if missing else "Back your \"%s\" story with evidence") % theme_row["name"],
            "why": "Interviews ask: \"%s\" %s" % (theme_row["ask"], "You have no story for it yet." if missing else
                                                 "Your story rests on your word alone."),
            "effort_hours": 2 if missing else 3, "expected_points": round(weight / 5.0, 1), "roles_affected": 0,
            "chance": 0.7 if missing else 0.4, "added_on": today,
            "done_when": ("A story in profile/stories.json for this theme, in your words, with its result"
                          if missing else "The story links to evidence at least corroborated (a link, a referee)"),
            "effects": [{"dimension": "D7", "delta": 1, "scope": {},
                         "note": "Story gap %s. Effort and chance are first estimates." % theme_row["id"]}],
            "notes": "Story theme %s." % theme_row["id"]}


# ------------------------------------------------------------------ dashboard, agents, checks


def page_data(doc, config, evidence_doc, asked=None):
    """asked: scripts/_practice.py summary() of the question bank, or None."""
    if doc is None:
        return None
    levels = levels_of(evidence_doc)
    rows = coverage(doc, config, evidence_doc, (asked or {}).get("struggled"))
    stories = [{"id": s["id"], "title": s["title"], "themes": s.get("themes") or [],
                "strength": strength(s, levels), "result": s.get("result", "")} for s in doc.get("stories") or []]
    return {"note": NOTE, "themes_note": THEMES_NOTE, "themes": rows, "stories": stories, "asked": asked,
            "gaps": sum(1 for r in rows if r["status"] != "backed")}


def static_html(block):
    if not block:
        return ""
    rows = "".join('<tr><th scope="row">%s</th><td>%s</td><td>%s</td></tr>' % (
        html.escape(r["name"]), html.escape(STATUS_NAMES[r["status"]]), html.escape(", ".join(r["stories"]) or "None"))
        for r in block["themes"])
    return ('<h3 id="staticStoriesH">Story bank</h3><p class="small sub">%s %s</p><table aria-labelledby="staticStoriesH">'
            '<thead><tr><th scope="col">Theme</th><th scope="col">Status</th><th scope="col">Stories</th></tr></thead>'
            '<tbody>%s</tbody></table>') % (html.escape(NOTE), html.escape(THEMES_NOTE), rows)


def summary_lines(block):
    if not block:
        return []
    lines = ["", "## Story bank (progress only: changes no score)", "- " + THEMES_NOTE]
    for r in block["themes"]:
        lines.append("- %s: %s%s." % (r["name"], STATUS_NAMES[r["status"]].lower(),
                                     " (%s)" % ", ".join(r["stories"]) if r["stories"] else ""))
    if block.get("asked"):
        a = block["asked"]
        lines.append("- Questions saved: %d from practice, %d from real interviews (%d rated gap)." % (
            a["practice"], a["real"], a["gaps"]))
    lines.append("- Never write a story for the person. Ask for theirs, then record it with `scripts/stories.py add`.")
    return lines


def checks(doc, config, evidence_ids, action_ids, errors, warnings):
    """validate.py's cross-file checks for profile/stories.json (the schema is checked separately)."""
    if doc is None:
        return
    known, seen = {t["id"] for t in themes(config)}, set()
    for s in doc.get("stories") or []:
        where = REL + ": " + str(s.get("id"))
        if s.get("id") in seen:
            errors.append(where + " is a duplicate id")
        seen.add(s.get("id"))
        for t in s.get("themes") or []:
            if t not in known:
                errors.append(where + " names theme %s, which is not a story theme" % t)
        for e in s.get("evidence") or []:
            if evidence_ids is not None and e not in evidence_ids:
                errors.append(where + " cites evidence %s, which is not in profile/evidence.json" % e)
    for t, a in (doc.get("actions") or {}).items():
        if action_ids is not None and a not in action_ids:
            warnings.append(REL + ": theme %s points at plan action %s, which is not in campaign/plan.json" % (t, a))
