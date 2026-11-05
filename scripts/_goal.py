"""The goal: how it is written down, and an honest test of it against the starting line.

A goal is a role, the organisations, where, and a date (config.json "goal":
role, organisations, where, by). Once there is a scored result, the goal is
tested against it: on the plan's own dates, does the best match reach the
level that counts as the goal (default Level 4, Good) by the goal date? There
are three honest answers: yes on expected odds, only if every move works, or
no plan gets there. When it is not a yes, LVLme proposes a stepping stone with
the reason, and the person chooses. Nothing is changed until they do.

The same functions give the starting line: the level, the fit range, and the
date the plan is expected to reach the next level (or the plain statement that
no plan gets there yet, and what is missing).

Nothing here is invented. The dates, levels and fits come from _levels.py, which
reads the scored runs and the plan. No network calls.
"""
import datetime as dt

import _common as C
import _levels as L

DEFAULT_TARGET_LEVEL = 4
SENTENCE_FIELDS = ("role", "organisations", "where", "by")


def long_date(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, d.strftime("%b"), d.year)


def short_date(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s" % (d.day, d.strftime("%b"))


def join_names(names):
    names = [n.strip() for n in names if n and n.strip()]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " or " + names[-1]


def goal_sentence(role, organisations, where, by):
    """One clear goal sentence that everything is measured against.

    >>> goal_sentence("Customer success", ["Anthropic", "OpenAI"], "Melbourne", "2027-06-30")
    'Customer success at Anthropic or OpenAI, in Melbourne, by 30 Jun 2027'
    """
    text = (role or "").strip()
    orgs = join_names(organisations or [])
    if orgs:
        text += " at " + orgs
    if (where or "").strip():
        text += ", in " + where.strip()
    if by:
        text += ", by " + long_date(by)
    return text.strip(", ")


def goal_line(goal):
    """The goal as one sentence, from the new fields when they are there, else from the title."""
    if goal.get("role"):
        return goal_sentence(goal["role"], goal.get("organisations"), goal.get("where"), goal.get("by"))
    return (goal.get("title") or "").strip().rstrip(".")


def target_level(goal):
    try:
        return min(5, max(2, int((goal or {}).get("target_level") or DEFAULT_TARGET_LEVEL)))
    except (TypeError, ValueError):
        return DEFAULT_TARGET_LEVEL


def judged_roles(page):
    return [r for r in page["roles"] if r.get("judged", True)]


def fit_range(role):
    """(low, high) when the role carries a range from two judgings (fit_low and fit_high), else (fit, fit).

    The range comes from the engine's run file (the shared contract: per role, fit_low and fit_high next to fit).
    Until the engine writes them there is only the single fit, and the page says so by showing one number."""
    lo, hi = role.get("lo"), role.get("hi")
    if lo is None or hi is None:
        return role["fit"], role["fit"]
    return min(lo, role["fit"]), max(hi, role["fit"])


def fit_text(role):
    """'fit about 18 to 25' with a range, 'fit 21' without one."""
    lo, hi = fit_range(role)
    if int(lo + 0.5) == int(hi + 0.5):
        return "fit %s" % ("%g" % L.r1(role["fit"]))
    return "fit about %d to %d" % (int(lo + 0.5), int(hi + 0.5))


def _acts_by(page, by):
    return [a for a in page["actions"] if L.is_live(a) and (not by or a["date"] <= by)]


def _threshold(level):
    return L.THRESH[level - 1]


def check(page, goal, today):
    """Test the goal against the starting line.

    Returns {"verdict", "target_level", "target_band", "by", "fit_now", "expected_by", "best_case_by", "reach_date",
    "text", "stepping_stone"}. verdict is reached, on_track, stretch, out_of_reach or unknown (nothing judged yet).
    """
    roles = judged_roles(page)
    tl = target_level(goal)
    out = {"target_level": tl, "target_band": C.BANDS[tl - 1], "by": goal.get("by"), "stepping_stone": None}
    if not roles:
        out.update(verdict="unknown", text="No role has been judged yet, so the goal cannot be tested honestly. "
                                           "It is tested as soon as the first roles are judged.")
        return out
    caps, weights = page["caps"], page["weights"]
    thr = _threshold(tl)
    every = L.best_of(roles, _acts_by(page, None), caps, weights, "exp", today=today)
    now = max(r["fit"] for r in roles)
    out["fit_now"] = now
    out["reach_date"] = L.cross_at(every["pts"], thr)
    by = goal.get("by")
    exp = L.best_of(roles, _acts_by(page, by), caps, weights, "exp", today=today)["fit"]
    best = L.best_of(roles, _acts_by(page, by), caps, weights, "best", today=today)["fit"]
    out.update(expected_by=exp, best_case_by=best)
    level_name = "Level %d (%s)" % (tl, C.BANDS[tl - 1])
    when = " by %s" % long_date(by) if by else ""
    if now >= thr:
        out.update(verdict="reached", text="Your best match is already at %s." % level_name)
    elif exp >= thr:
        out.update(verdict="on_track", text="On the plan's dates your best match is expected to reach %s%s%s." % (
            level_name, when, " (about %s)" % short_date(out["reach_date"]) if out["reach_date"] and by else ""))
    elif best >= thr:
        out.update(verdict="stretch", text="Only if every move works does your best match reach %s%s. On expected odds "
                                           "it reaches about %d." % (level_name, when, int(exp + 0.5)))
    else:
        out.update(verdict="out_of_reach", text="No plan reaches %s%s. The plan gets your best match to about %d, "
                                                "and %d is needed." % (level_name, when, int(exp + 0.5), thr))
    if out["verdict"] in ("stretch", "out_of_reach"):
        out["stepping_stone"] = stepping_stone(page, goal, roles, today, exp, by, thr, level_name)
        if out["stepping_stone"] is None:
            out["text"] += " There is no smaller step to propose, so the choices are a later date or more moves in the plan."
    return out


def _role_where(role):
    return (role.get("loc") or [""])[0]


def stepping_stone(page, goal, roles, today, exp, by, thr, level_name):
    """The highest level the plan does reach by the goal date, named as a step, with the reason."""
    caps, weights = page["caps"], page["weights"]
    held = L.best_of(roles, _acts_by(page, by), caps, weights, "exp", today=today)
    holder = held["role"]
    now = max(r["fit"] for r in roles)
    reach = next((lv for lv in range(target_level(goal) - 1, 0, -1) if exp >= _threshold(lv) and _threshold(lv) > now), None)
    base = {"role": holder["title"], "organisations": [holder["on"]], "where": _role_where(holder)}
    if reach:
        base.update(level=reach, by=by,
                    why="On the plan's dates your best match reaches about %d by %s, which is Level %d (%s), not %s. "
                        "Level %d first is a real step you can reach, and it moves the evidence toward the goal." % (
                            int(exp + 0.5), long_date(by) if by else "the end of the plan", reach, C.BANDS[reach - 1],
                            level_name, reach))
        base["title"] = "Reach Level %d (%s) first, as %s at %s" % (reach, C.BANDS[reach - 1], holder["title"], holder["on"])
        return base
    nl = L.next_level(L.journey_roles(roles), page["actions"], caps, weights, today)
    nxt = nl.get("next_level")
    if nxt is None or nxt >= target_level(goal):
        return None      # the next level is the goal itself: there is no smaller step to propose
    date = (nl.get("set") or {}).get("date")
    base.update(level=nxt, by=date,
                why="No plan reaches %s%s. The nearest honest step is Level %d (%s)%s, so the first goal is to climb one level." % (
                    level_name, " by %s" % long_date(by) if by else "", nxt, C.BANDS[nxt - 1],
                    " around %s" % short_date(date) if date else " once more moves are added to the plan"))
    base["title"] = "Reach Level %d (%s) first" % (nxt, C.BANDS[nxt - 1])
    return base


def starting_line(page, today):
    """The starting line: level, fit range and the date the plan is expected to reach the next level.

    Returns a dict with level, band, fit, range text, chance word, next_level, date, moves, chance and a plain
    sentence in "next". When no plan gets there it says so and names what is missing."""
    roles = judged_roles(page)
    if not roles:
        return None
    rs = L.journey_roles(roles)
    nl = L.next_level(rs, page["actions"], page["caps"], page["weights"], today)
    lead = rs[0]
    out = {"role_id": lead["id"], "role": lead["title"], "org": lead["on"], "fit": lead["fit"], "fit_text": fit_text(lead),
           "fit_low": fit_range(lead)[0], "fit_high": fit_range(lead)[1], "has_range": fit_range(lead)[0] != fit_range(lead)[1],
           "level": nl["level"], "band": nl["band"], "chance_word": lead.get("ib"), "top": nl["top"]}
    if nl["top"]:
        out.update(next="You are at the top level. Keep the evidence fresh so you stay there.", date=None, moves=0, reachable=True)
        return out
    out.update(next_level=nl["next_level"], next_band=nl["next_band"], points_to_next=nl["points_to_next"])
    lvl = "Level %d" % nl["next_level"]
    if nl["reachable"]:
        s = nl["set"]
        n = len(s["ids"])
        names = {a["id"]: a["title"] for a in page["actions"]}
        out.update(reachable=True, date=s["date"], moves=n, move_titles=[names.get(i, i) for i in s["ids"]],
                   chance=s.get("chance"),
                   next="%s expected by %s with %s." % (lvl, short_date(s["date"]) if s["date"] else "the plan's dates",
                                                         "this move" if n == 1 else "these %s moves" % _number(n)))
        return out
    missing = nl["missing"]
    room = [C.DIMENSION_NAMES[x["dimension"]].lower() for x in missing["room"][:3]]
    out.update(reachable=False, date=None, moves=0, missing=missing["room"], points_short=missing["points"],
               next="No plan gets you to %s yet: the plan is about %s points short. %s" % (
                   lvl, "%g" % missing["points"],
                   ("What is missing: %s." % join_names(room)) if room else "Add moves that raise what is missing."))
    return out


def _number(n):
    return {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}.get(n, str(n))
