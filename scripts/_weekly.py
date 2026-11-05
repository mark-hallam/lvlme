"""The weekly rhythm: a Monday plan note, a Friday review, and the weeks in a row with real evidence.

The Monday note is campaign/weekly/<monday>.md (what changed, the level, the one move, when the next level is
expected). The Friday review is campaign/weekly/<friday>-review.md and .json: what was done with evidence, what
moved, next week's one move. A week counts toward the streak only when it showed real progress (_levels.progress_days:
a role gained fit, evidence was checked, or a plan action was finished with evidence). Drafts and notes only: nothing
is sent. No network calls.
"""
import datetime as dt
import glob
import os

import _common as C
import _levels as L

WEEKLY = ("campaign", "weekly")
CHECKED = L.CHECKED


def monday_of(iso):
    d = dt.date.fromisoformat(iso)
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def friday_of(iso):
    return (dt.date.fromisoformat(monday_of(iso)) + dt.timedelta(days=4)).isoformat()


def week_key(iso):
    y, w, _ = dt.date.fromisoformat(iso).isocalendar()
    return (y, w)


def weeks_in_a_row(progress_days, today):
    """How many weeks in a row, up to this one, showed real progress.

    The current week counts when it already has progress; when it has none yet the week is not over, so the count
    starts from last week. A week with a scored day and no progress ends the count, and so does a week with no scored
    day at all.

    >>> days = [{"date": "2026-10-20", "progress": True}, {"date": "2026-10-28", "progress": True}]
    >>> weeks_in_a_row(days, "2026-10-30")
    2
    """
    weeks = {week_key(d["date"]) for d in progress_days if d.get("progress")}
    d = dt.date.fromisoformat(today)
    cur = week_key(today)
    if cur not in weeks:
        d -= dt.timedelta(days=7)
    n = 0
    while week_key(d.isoformat()) in weeks:
        n += 1
        d -= dt.timedelta(days=7)
    return n


def latest(ws, today):
    """The newest Monday plan note and the newest Friday review on or before today, as data: {"plan", "review"}.
    Either is None when the agent has not written one yet."""
    plan = review = None
    for f in sorted(glob.glob(C.wpath(ws, *WEEKLY, "*.json"))):
        name = os.path.basename(f)
        if name[:10] > today:
            continue
        doc = C.load_json(f, None)
        if not isinstance(doc, dict):
            continue
        if name.endswith("-review.json"):
            review = doc
        else:
            plan = doc
    return {"plan": plan, "review": review}


def plural(n, one, many=None):
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def streak_text(n):
    if n <= 0:
        return "No weeks in a row yet: a week counts when something is finished or checked with evidence."
    return "%s in a row with real evidence." % plural(n, "week")


def _runs(ws):
    out = []
    for f in sorted(glob.glob(C.wpath(ws, "eval", "runs", "*.json"))):
        run = C.load_json(f, {}) or {}
        if (run.get("counts") or {}).get("judged", 1):
            out.append(run)
    return out


def _best(run):
    fits = [r["fit"] for r in run.get("roles") or [] if r.get("judged", True) and r.get("fit") is not None]
    return max(fits) if fits else None


def review(ws, config, friday, today, dash):
    """The Friday review as data. dash is report/for-agents/dashboard.json (may be empty)."""
    monday = monday_of(friday)
    plan = C.load_json(C.wpath(ws, "campaign", "plan.json"), {}) or {}
    evidence = C.load_json(C.wpath(ws, "profile", "evidence.json"), {}) or {}
    end = min(today, (dt.date.fromisoformat(monday) + dt.timedelta(days=6)).isoformat())   # the week runs Monday to Sunday
    done = [{"id": a["id"], "title": a.get("title", a["id"]), "evidence": a.get("done_evidence")}
            for a in plan.get("actions") or []
            if a.get("status") == "done" and a.get("done_evidence") and monday <= (a.get("finished_on") or "") <= end]
    counted = [{"id": e["id"], "title": e.get("title") or e.get("claim") or e["id"]} for e in evidence.get("items") or []
               if e.get("level") in CHECKED and any(monday <= d <= end for d in _checked(e))]
    runs = _runs(ws)
    before = [r for r in runs if r["run_date"] < monday]
    inside = [r for r in runs if r["run_date"] <= end]
    moved = {"changed": False, "text": "No scored run yet, so nothing can be compared."}
    if inside:
        now, start = inside[-1], (before[-1] if before else None)
        if start is None:
            moved = {"changed": False, "text": "This is the first scored week: next week's review says what moved."}
        elif start.get("rubric_version") != now.get("rubric_version"):
            moved = {"changed": False, "text": "The scoring rules changed from version %s to %s, so this week's change is not comparable." % (
                start.get("rubric_version"), now.get("rubric_version"))}
        else:
            a, b = _best(start), _best(now)
            la, lb = L.band_index(a) + 1, L.band_index(b) + 1
            delta = round(b - a, 1)
            text = "Best fit %s, from %s to %s." % (("up %g" % delta) if delta > 0 else ("down %g" % -delta) if delta < 0 else "unchanged", "%g" % a, "%g" % b)
            if lb != la:
                text += " Level %d to Level %d." % (la, lb)
            moved = {"changed": delta != 0, "text": text, "from": a, "to": b, "level_from": la, "level_to": lb}
    moves = (dash.get("levels") or {}).get("quests") or []
    nxt = moves[0] if moves else None
    streak = weeks_in_a_row(((dash.get("levels") or {}).get("progress_days")) or [], friday if friday <= today else today)
    return {"schema_version": 1, "kind": "review", "date": friday, "week_of": monday, "done": done, "evidence": counted,
            "moved": moved, "next_move": {"id": nxt["id"], "title": nxt["title_on_page"] or nxt["title"], "why": nxt.get("done_when", "")} if nxt else None,
            "weeks_in_a_row": streak, "streak_text": streak_text(streak)}


def _checked(item):
    dates = [s.get("checked_on") for s in item.get("sources") or [] if s.get("checked_on")]
    return dates or ([item["added_on"]] if item.get("added_on") else [])


def long(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s" % (d.day, d.strftime("%b"))


def review_md(r):
    lines = ["# Review of the week of %s" % long(r["week_of"]), ""]
    if r["done"]:
        lines += ["Done with evidence this week:", ""]
        lines += ["- %s (evidence: %s)" % (d["title"].rstrip("."), str(d["evidence"]).strip()) for d in r["done"]]
    else:
        lines += ["No move was finished with evidence this week."]
    if r["evidence"]:
        lines += ["", "Evidence checked this week:", ""] + ["- %s" % e["title"] for e in r["evidence"]]
    lines += ["", "What moved: %s" % r["moved"]["text"], ""]
    if r["next_move"]:
        lines.append("Next week's one move: %s." % r["next_move"]["title"].rstrip("."))
    else:
        lines.append("Next week's one move: nothing new in the plan. Ask your agent to add the next move.")
    lines += ["", r["streak_text"]]
    return "\n".join(lines) + "\n"


def write_review(ws, config, date, today, dash):
    """Write campaign/weekly/<friday>-review.md and .json for the week that date falls in. Returns the review."""
    friday = friday_of(date)
    r = review(ws, config, friday, today, dash)
    C.write_json(C.wpath(ws, *WEEKLY, friday + "-review.json"), r)
    C.write_text(C.wpath(ws, *WEEKLY, friday + "-review.md"), review_md(r))
    return r
