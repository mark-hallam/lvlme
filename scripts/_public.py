"""Build in public (campaign/public.json): what to share, drafts in the person's voice, and a steady rhythm.

Showing your work in public is how people who could hire or refer you get to
know it, and it is the public signal factor (D5). LVLme plans and drafts; the
person posts, under their own name, every time. It never posts, and it never
opens LinkedIn.

  ideas()    things the person finished recently that are worth sharing: plan
             actions done on proof, organisation edge or public signal (D2,
             D4, D5), checked artefacts with a public link, and events they
             went to. Never anything about a named person. An idea already
             drafted or posted is not suggested again.
  cadence()  posts per week against the person's own target
             (config.json public.per_week, default 1), and the run of weeks
             that met it.
  A post counts as proof only once its public link has been opened and checked
  (scripts/public.py checked): then it becomes a verified public_signal
  evidence item, which the next run can judge. Until then it is the person's
  word. No network calls here.
"""
import datetime as dt
import html
import re

REL = "campaign/public.json"
CHANNELS = ["x", "linkedin", "blog", "github", "newsletter", "talk", "other"]
CHANNEL_NAMES = {"x": "X", "linkedin": "LinkedIn", "blog": "Blog", "github": "GitHub", "newsletter": "Newsletter",
                 "talk": "Talk", "other": "Other"}
STATUSES = ["drafted", "posted", "skipped"]
SHARE_DIMS = ("D2", "D4", "D5")
LOOKBACK_DAYS, WEEKS_SHOWN = 21, 4
DEFAULT_VOICE = ("Short (under about 70 words for X and LinkedIn). Plain words, the person's own way of saying "
                 "things. Say what you made or learned and one thing you noticed. No hashtags, no hype words.")
NOTE = "LVLme drafts; you post, under your name. A post counts as proof once its public link is checked."


def settings(config):
    p = (config or {}).get("public") or {}
    return {"per_week": p.get("per_week", 1), "channels": p.get("channels") or ["x", "linkedin"],
            "voice": p.get("voice") or DEFAULT_VOICE}


def empty():
    return {"schema_version": 1, "posts": []}


def days(a, b):
    try:
        return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return 10 ** 6


def week_start(date):
    d = dt.date.fromisoformat(date)
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def used_refs(doc):
    return {p["about"] for p in (doc or {}).get("posts") or [] if p.get("about") and p.get("status") != "skipped"}


def ideas(plan, evidence_doc, doors_doc, doc, today):
    """[{"ref", "kind", "title", "why", "on"}], newest first."""
    out, used = [], used_refs(doc)
    for a in (plan or {}).get("actions") or []:
        if a.get("status") == "done" and a.get("dimension") in SHARE_DIMS and days(a.get("finished_on"), today) <= LOOKBACK_DAYS:
            out.append({"ref": a["id"], "kind": "action", "title": a["title"], "on": a["finished_on"],
                        "why": "You finished it on %s: say what you made and what you learned." % a["finished_on"]})
    shown = {a.get("done_evidence") for a in (plan or {}).get("actions") or []      # one thing, one idea: an artefact
             if a["id"] in used or a["id"] in {i["ref"] for i in out}}               # a finished action already shows
    for e in (evidence_doc or {}).get("items") or []:
        link = next((s["ref"] for s in e.get("sources") or [] if str(s.get("ref", "")).startswith("https://")), None)
        if (e.get("kind") == "artefact" and e.get("level") in ("verified", "corroborated") and link
                and link not in shown and days(e.get("added_on"), today) <= LOOKBACK_DAYS):
            out.append({"ref": e["id"], "kind": "evidence", "title": e["claim"], "on": e.get("added_on"),
                        "why": "Checked and public (%s): show it to people who could use it." % link})
    for d in (doors_doc or {}).get("doors") or []:
        on = d.get("starts_on") or d.get("closes_on")
        if d.get("status") == "went" and days(on, today) <= LOOKBACK_DAYS:
            out.append({"ref": d["id"], "kind": "door", "title": "What you took away from %s" % d["title"], "on": on,
                        "why": "You went on %s. Share one thing you learned (no one's name without their yes)." % on})
    return sorted([i for i in out if i["ref"] not in used], key=lambda i: (i["on"] or "", i["ref"]), reverse=True)


def cadence(doc, config, today):
    """{"per_week", "this_week", "weeks": [{"start", "posted"}], "streak", "due"} for the last WEEKS_SHOWN weeks."""
    per = settings(config)["per_week"]
    posted = [p["posted_on"] for p in (doc or {}).get("posts") or [] if p.get("status") == "posted" and p.get("posted_on")]
    start = dt.date.fromisoformat(week_start(today))
    weeks = []
    for i in range(WEEKS_SHOWN - 1, -1, -1):
        s = (start - dt.timedelta(weeks=i)).isoformat()
        weeks.append({"start": s, "posted": sum(1 for d in posted if week_start(d) == s)})
    streak = 0
    for w in reversed(weeks[:-1]):                     # finished weeks only; this week can still be met
        if w["posted"] < per:
            break
        streak += 1
    if weeks[-1]["posted"] >= per:
        streak += 1
    return {"per_week": per, "this_week": weeks[-1]["posted"], "weeks": weeks, "streak": streak,
            "due": max(0, per - weeks[-1]["posted"])}


def next_id(doc):
    n = max([int(p["id"][1:]) for p in (doc or {}).get("posts") or [] if re.match(r"^P\d+$", p.get("id", ""))] or [0])
    return "P%02d" % (n + 1)


def brief(post, idea, config, facts):
    """The draft file: the facts, the person's voice rules, and room for the draft. The agent writes the draft
    there from the person's own notes; the person edits it and posts it themselves."""
    s = settings(config)
    return "\n".join([
        "# Build in public: %s" % idea["title"], "",
        "Draft only. LVLme never posts. Edit it until it sounds like you, post it yourself, then tell your agent "
        "the link so it can be checked and counted.", "",
        "- Post id: %s. Channel: %s." % (post["id"], CHANNEL_NAMES.get(post["channel"], post["channel"])),
        "- About: %s (%s)." % (idea["title"], idea["ref"]),
        "- Why now: %s" % idea["why"], "",
        "## Facts it may use (and nothing else)", ""] + ["- " + f for f in facts] + [
        "", "## Your voice", "", s["voice"], "",
        "## Your notes", "", "[What you want to say, in your own rough words. The draft starts from these.]", "",
        "## Draft", "", "[Written from your notes, in your voice. No number or claim beyond the facts above.]", ""])


def page_data(doc, config, plan, evidence_doc, doors_doc, today):
    c = cadence(doc, config, today)
    found = ideas(plan, evidence_doc, doors_doc, doc, today)
    posts = sorted((doc or {}).get("posts") or [], key=lambda p: p.get("posted_on") or p.get("drafted_on") or "",
                   reverse=True)
    if not posts and not found:
        return None
    return {"note": NOTE, "cadence": c, "ideas": found[:3], "more_ideas": max(0, len(found) - 3),
            "drafts": [{"id": p["id"], "title": p.get("title", ""), "channel": CHANNEL_NAMES.get(p["channel"], ""),
                        "file": p.get("draft_file", "")} for p in posts if p.get("status") == "drafted"],
            "posts": [{"id": p["id"], "title": p.get("title", ""), "channel": CHANNEL_NAMES.get(p["channel"], ""),
                       "on": p.get("posted_on"), "url": p.get("url", ""), "checked": bool(p.get("evidence")),
                       "result": p.get("result", "")} for p in posts if p.get("status") == "posted"][:5]}


def static_html(block):
    if not block:
        return ""
    c = block["cadence"]
    items = ["%d of %d post%s this week; %d week%s in a row on target." % (
        c["this_week"], c["per_week"], "" if c["per_week"] == 1 else "s", c["streak"], "" if c["streak"] == 1 else "s")]
    items += ["Idea: %s" % i["title"] for i in block["ideas"]]
    items += ["Posted %s on %s: %s%s" % (p["on"], p["channel"], p["title"], "" if p["checked"] else " (link not checked yet)")
              for p in block["posts"]]
    return '<h3>Build in public</h3><p class="small sub">%s</p><ul class="small">%s</ul>' % (
        html.escape(NOTE), "".join("<li>%s</li>" % html.escape(t) for t in items))


def summary_lines(block):
    if not block:
        return []
    c = block["cadence"]
    lines = ["", "## Build in public (drafts only: the person posts)",
             "- This week: %d of %d post%s. Weeks in a row on target: %d." % (
                 c["this_week"], c["per_week"], "" if c["per_week"] == 1 else "s", c["streak"])]
    lines += ["- Idea (%s): %s. %s" % (i["ref"], i["title"], i["why"]) for i in block["ideas"]]
    lines += ["- Draft waiting: %s (%s)." % (d["title"], d["file"]) for d in block["drafts"]]
    lines.append("- Draft one with `scripts/public.py draft <idea ref>`; never post for the person.")
    return lines


def checks(doc, evidence_ids, errors):
    if doc is None:
        return
    seen = set()
    for p in doc.get("posts") or []:
        where = REL + ": " + str(p.get("id"))
        if p.get("id") in seen:
            errors.append(where + " is a duplicate id")
        seen.add(p.get("id"))
        if p.get("status") == "posted" and not p.get("posted_on"):
            errors.append(where + " is posted with no posted_on date")
        if p.get("evidence") and evidence_ids is not None and p["evidence"] not in evidence_ids:
            errors.append(where + " names evidence %s, which is not in profile/evidence.json" % p["evidence"])
