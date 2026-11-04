"""Level maths for the dashboard: the projection, levels, the next-level set, quests, level history and streak.

Levels are the fit bands of method/RUBRIC.md, numbered 1 to 5: Level 1 Very low
(fit 0 to 39), Level 2 Low (40 to 54), Level 3 Moderate (55 to 69), Level 4 Good
(70 to 84), Level 5 Strong (85 to 100). They use the fit score itself, before
the referral and hard-requirement adjustments, so "points to the next level" is
a plain distance on the fit scale.

Every number here comes from the scored runs (eval/runs/*.json), the evidence
file and campaign/plan.json. Nothing is invented: there are no experience
points, only fit points the rubric and the plan's effects give.

The page script mirrors this module (JS_LEVELS in _dashboard_assets.py), so the
what-if switches and the organisation selector can recompute it in the browser.
Keep the two in step: same order of operations, same tie-breaks.

Projection: open actions apply in target-date order; each effect raises a
factor by `delta` or to `set_at_least`, only for roles in its scope; a factor
never rises more than the projection cap over today's score, or above 5; the
expected path weights each rise by the action's chance of working, the best
case assumes it works. A role whose eligibility blocker cannot be cleared keeps
eligibility at its score today.

The level follows the best fit across the roles a journey follows (every role,
or one organisation's), as the level history does, so an action can reach the
next level by lifting a role other than today's best. The next-level set, its
date and chance, and each quest's points are all measured on that best fit; the
role that then holds it is named wherever it is not today's best. The page calls
that best fit the "best match".

Up next is the one ranked list of actions the page shows (up_next): the actions
on the path to the next level first, in target-date order, then the rest by
points per hour. Each row shows one number, the quest's expected points.
"""
import itertools
import math

import _common as C

DIMS = C.DIMENSIONS
BANDS = C.BANDS
THRESH = [0, 40, 55, 70, 85]
MAX_EXACT = 14          # search every combination up to this many actions; beyond it, a greedy search (flagged)
CHECKED = ("verified", "corroborated")


def r1(v):
    """Round to one decimal place, half up (the same as Math.round(v * 10) / 10 in the page)."""
    return math.floor(v * 10 + 0.5) / 10.0


def pct(p):
    return int(math.floor(p * 100 + 0.5))


def band_index(fit):
    """0 for Very low up to 4 for Strong."""
    return 4 if fit >= 85 else 3 if fit >= 70 else 2 if fit >= 55 else 1 if fit >= 40 else 0


def fit_of(s, weights):
    total = sum(weights) or 1
    return r1(sum(v / 5.0 * w for v, w in zip(s, weights)) * 100.0 / total)


def in_scope(role, scope):
    for key, value in (("orgs", role["org"]), ("families", role["family"]),
                       ("location_classes", role["lc"]), ("role_ids", role["id"])):
        allowed = scope.get(key) or []
        if allowed and value not in allowed:
            return False
    return True


def is_live(a):
    return a.get("status") in ("todo", "doing")


def walk(role, actions, caps, weights, mode="exp", sure=None, today=None):
    """Apply the open actions in list order (target-date order).

    Returns (points, scores): points is [(date, fit)], starting with today and
    one more after each action; scores are the seven factor scores at the end.
    `sure` names one action treated as certain to work (its "if it works" case)."""
    base, s = list(role["s"]), list(role["s"])
    pts = [(today, role["fit"])]
    for a in actions:
        if not is_live(a):
            continue
        p = 1.0 if mode == "best" or a["id"] == sure else a["p"]
        for e in a["effects"]:
            if e.get("dimension") not in DIMS or not in_scope(role, e.get("scope") or {}):
                continue
            k = DIMS.index(e["dimension"])
            if k == 5 and role.get("hard"):
                continue  # a blocker the plan can't clear keeps eligibility where it is
            cur = s[k]
            new = cur + e["delta"] if "delta" in e else max(cur, e.get("set_at_least", 0))
            new = min(5, new, base[k] + caps[k])
            if new > cur:
                s[k] = cur + p * (new - cur)
        d = a.get("date")
        pts.append((today if today and d and d < today else d, fit_of(s, weights)))
    return pts, s


def project(role, actions, caps, weights, mode="exp", sure=None):
    """(fit, scores) at the end date. Mirrors project() in the page script."""
    _, s = walk(role, actions, caps, weights, mode, sure)
    return fit_of(s, weights), s


def cross_at(pts, target):
    for d, v in pts:
        if v >= target:
            return d
    return None


def best_of(roles, actions, caps, weights, mode="exp", sure=None, today=None):
    """The best fit across roles after the same actions: every role is walked, and the highest end fit kept.

    Returns {"fit", "role", "scores", "pts"}: the best fit at the end, the role holding it (ties go to the
    role listed first, so today's best wins a tie), that role's factor scores, and pts, the best fit across
    the roles at each step [(date, fit)]. The level is the band of this best fit, so any role can carry it."""
    if not roles:
        return None
    best, path = None, None
    for r in roles:
        pts, s = walk(r, actions, caps, weights, mode, sure, today)
        end = fit_of(s, weights)
        if best is None or end > best["fit"]:
            best = {"fit": end, "role": r, "scores": s}
        path = pts if path is None else [(d, max(v, w)) for (d, v), (_, w) in zip(path, pts)]
    best["pts"] = path
    return best


def journey_roles(roles, lead=None, group=None):
    """The roles a journey follows, today's best first: every role (the page keeps them best first),
    or one organisation group's roles with its best role (lead) first."""
    if group is None:
        return list(roles)
    return [lead] + [r for r in roles if r.get("g") == group and r is not lead]

# ------------------------------------------------------------ next level


def raises(role, a, caps, weights):
    """True if the action, if it works, raises at least one of this role's factors."""
    _, s = project(role, [a], caps, weights, "best")
    return any(x > y + 1e-9 for x, y in zip(s, role["s"]))


def _hours(acts):
    total = 0.0
    for a in acts:
        total += a.get("hours", 0) or 0
    return total


def _found(acts, w, target, exact):
    return {"ids": [a["id"] for a in acts], "acts": list(acts), "date": cross_at(w["pts"], target),
            "fit": w["fit"], "exact": exact, "role": w["role"]}


def smallest_set(roles, acts, target, caps, weights, mode, today):
    """The fewest actions (from acts, kept in date order) that take the best fit across roles to target.

    Ties go to the earliest date the level is reached, then the least effort,
    then the higher fit, then the action ids. Returns None if even all of them
    together fall short. role in the result is the role that then holds the best fit."""
    if not roles or best_of(roles, acts, caps, weights, mode)["fit"] < target:
        return None
    if len(acts) > MAX_EXACT:
        return _greedy_set(roles, acts, target, caps, weights, mode, today)
    for k in range(1, len(acts) + 1):
        best = None
        for combo in itertools.combinations(acts, k):
            w = best_of(roles, combo, caps, weights, mode, today=today)
            if w["fit"] < target:
                continue
            key = (cross_at(w["pts"], target), _hours(combo), -w["fit"], ",".join(a["id"] for a in combo))
            if best is None or key < best[0]:
                best = (key, combo, w)
        if best:
            return _found(best[1], best[2], target, True)
    return None


def _greedy_set(roles, acts, target, caps, weights, mode, today):
    """For long plans: add the action with the most fit gained per hour until the target is reached,
    then drop any action the rest can do without (latest first). Flagged as not exact."""
    def fit(lst):
        return best_of(roles, lst, caps, weights, mode)["fit"]

    def in_order(lst):
        return [a for a in acts if a in lst]
    chosen = []
    while fit(chosen) < target:
        cur, pick, rate = fit(chosen), None, -1.0
        for a in acts:
            if a in chosen:
                continue
            gain = fit(in_order(chosen + [a])) - cur
            r = gain / (a.get("hours") or 1)
            if gain > 0 and r > rate:
                pick, rate = a, r
        if pick is None:
            return None
        chosen = in_order(chosen + [pick])
    for i in range(len(chosen) - 1, -1, -1):
        rest = chosen[:i] + chosen[i + 1:]
        if fit(rest) >= target:
            chosen = rest
    return _found(chosen, best_of(roles, chosen, caps, weights, mode, today=today), target, False)


def chance_of(roles, acts, target, caps, weights):
    """The chance the level is actually reached by these actions, treating each action's chance of
    working as independent: every works or fails outcome is projected, and the chances of the
    outcomes that take any of the roles to the target are added up. None for sets too long to enumerate."""
    n = len(acts)
    if n > MAX_EXACT:
        return None
    total = 0.0
    for m in range(1 << n):
        pr, works = 1.0, []
        for i, a in enumerate(acts):
            if (m >> i) & 1:
                pr *= a["p"]
                works.append(a)
            else:
                pr *= 1 - a["p"]
        if pr > 0 and any(project(r, works, caps, weights, "best")[0] >= target for r in roles):
            total += pr
    return total


def next_level(roles, actions, caps, weights, today):
    """What gets the best fit across these roles to the next level.

    roles: the roles the journey follows (every role, or one organisation's), today's best first.
    actions: the page actions, in target-date order (only open ones count).
    The level is the band of the best fit among the roles, so the next level is
    reached when any of them crosses the line, not only today's best. Returns
    the current level, the points to the next, and either the smallest set of
    open actions whose expected effects (weighted by their chance of working,
    within the caps) reach it, with the date that happens if they land on their
    target dates and the role they lift there, or, when no set does, how far
    short the whole plan falls, the best-case set, and the room left under the
    caps factor by factor on the role the plan takes closest."""
    lead = roles[0]
    idx = band_index(lead["fit"])
    out = {"role_id": lead["id"], "fit": lead["fit"], "level": idx + 1, "band": BANDS[idx], "top": idx >= 4}
    if out["top"]:
        return out
    target = THRESH[idx + 1]
    acts = [a for a in actions if is_live(a)]
    rel = [a for a in acts if any(raises(r, a, caps, weights) for r in roles)]
    every = best_of(roles, acts, caps, weights, "exp", today=today)
    out.update(target=target, next_level=idx + 2, next_band=BANDS[idx + 1], points_to_next=r1(target - lead["fit"]),
               relevant=[a["id"] for a in rel],
               plan={"fit_expected": every["fit"], "fit_best": best_of(roles, acts, caps, weights, "best")["fit"],
                     "date": cross_at(every["pts"], target)})
    # Only roles that could reach the line if every helpful action worked can carry the level there.
    cands = [r for r in roles if project(r, rel, caps, weights, "best")[0] >= target]
    use = [a for a in rel if any(raises(r, a, caps, weights) for r in cands)]
    found = smallest_set(cands, use, target, caps, weights, "exp", today)
    out["reachable"] = found is not None
    if found:
        found["chance"] = chance_of(cands, found["acts"], target, caps, weights)
        out["set"] = found
        return out
    best = smallest_set(cands, use, target, caps, weights, "best", today)
    if best:
        best["chance"] = chance_of(cands, best["acts"], target, caps, weights)
    out["best_case"] = best
    out["missing"] = _missing(every, rel, target, caps, weights)
    return out


def _missing(every, rel, target, caps, weights):
    """Room left under the caps, factor by factor, on the role the whole plan takes closest to the target."""
    role, s = every["role"], every["scores"]
    ceil = [v if (k == 5 and role.get("hard")) else min(5, v + caps[k]) for k, v in enumerate(role["s"])]
    total = sum(weights) or 1
    covered = [False] * len(DIMS)
    for a in rel:
        _, after = project(role, [a], caps, weights, "best")
        covered = [c or after[k] > role["s"][k] + 1e-9 for k, c in enumerate(covered)]
    room = [{"dimension": d, "points": r1((ceil[k] - s[k]) * weights[k] / 5.0 * 100.0 / total), "covered": covered[k]}
            for k, d in enumerate(DIMS)]
    room = sorted([x for x in room if x["points"] > 0], key=lambda x: (-x["points"], DIMS.index(x["dimension"])))
    return {"points": r1(target - every["fit"]), "ceiling": fit_of(ceil, weights), "room": room, "role": role}


def quests(roles, actions, caps, weights, nl, enabled=None):
    """Every open action as a quest: the points it brings toward the next level on its own.

    roles: as for next_level, today's best first. exp: the best fit across the
    roles after this action alone (weighted by its chance, within the caps),
    minus the best fit today; role is the role that then holds the best fit
    (today's best unless another role ends higher) and fit_after its fit. works: the same if it works. rate: exp
    per hour; quests are sorted by it. lead_exp and lead_works: what the action
    alone adds to today's best role (shown second when role differs).
    critical: in the smallest set that reaches the next level. best_case: in
    the best-case set (shown only when no set reaches it on expected odds).
    Points are counted one action at a time, so actions that raise the same
    factor overlap and their points do not simply add up."""
    lead = roles[0]
    acts = [a for a in actions if is_live(a)]
    on = set(a["id"] for a in acts) if enabled is None else set(enabled)
    crit = set((nl.get("set") or {}).get("ids") or [])
    bc = set((nl.get("best_case") or {}).get("ids") or [])
    out = []
    for a in acts:
        w = best_of(roles, [a], caps, weights, "exp")
        ok = best_of(roles, [a], caps, weights, "exp", sure=a["id"])
        exp, works = r1(w["fit"] - lead["fit"]), r1(ok["fit"] - lead["fit"])
        rate = exp / a["hours"] if a.get("hours") else 0.0
        out.append({"a": a, "exp": exp, "works": works, "rate": rate, "crit": a["id"] in crit, "bc": a["id"] in bc,
                    "on": a["id"] in on, "role": w["role"], "fit_after": w["fit"],
                    "lead_exp": r1(project(lead, [a], caps, weights, "exp")[0] - lead["fit"]),
                    "lead_works": r1(project(lead, [a], caps, weights, "best")[0] - lead["fit"])})
    # an action whose roles all look suspicious (scripts/_posting_checks.py) goes after the rest
    out.sort(key=lambda q: (bool(q["a"].get("susp")), -q["rate"], -q["exp"], -q["a"].get("priority", 0),
                            q["a"]["date"], q["a"]["id"]))
    return out


def path_ids(nl):
    """The actions on the path to the next level: the smallest set that gets there counting each action's
    chance, or, when no set does, the best-case set (every action in it must work). Empty at the top level,
    or when not even the best case gets there."""
    if nl.get("top"):
        return []
    found = nl.get("set") if nl.get("reachable") else nl.get("best_case")
    return list((found or {}).get("ids") or [])


def up_next(qs, nl):
    """The one ranked list of actions the dashboard shows as "Up next", everywhere outside the What if rail.

    qs: quests() for the same journey. The actions on the path to the next level come first, in
    target-date order (the order the Level up panel lists them), then the rest as quests() sorts them,
    most points per hour first. Each keeps its quest numbers; the page shows one, exp. Mirrors upNext()
    in the page script."""
    path = set(path_ids(nl))
    first = sorted((q for q in qs if q["a"]["id"] in path), key=lambda q: (q["a"]["date"], q["a"]["id"]))
    return first + [q for q in qs if q["a"]["id"] not in path]


def tell_agent(a):
    """The instruction the dashboard copies for "Mark done"."""
    return 'Mark action %s done ("%s"). Evidence: <paste a link, file path or email reference>. Done when: %s' % (
        a["id"], a["title"], a.get("done_when") or "see the plan")

# --------------------------------------------------------- history, streak


def level_history(runs, key="best"):
    """Each scored day's level for the best role overall (key "best") or at one organisation group,
    from the page runs ({date, top, orgs}). change is "up" or "down" when the band moved."""
    out, prev = [], None
    for rn in runs:
        v = rn["top"] if key == "best" else (rn.get("orgs") or {}).get(key)
        if v is None:
            continue
        lv = band_index(v)
        version_changed = bool(out and out[-1].get("rubric_version") != rn.get("rubric_version"))
        out.append({"date": rn["date"], "rubric_version": rn.get("rubric_version"), "fit": v, "level": lv + 1, "band": BANDS[lv],
                    "change": None if prev is None or version_changed or lv == prev else "up" if lv > prev else "down",
                    "not_comparable": version_changed,
                    "from_level": None if prev is None else prev + 1})
        prev = lv
    return out


def _checked_dates(item):
    dates = [s.get("checked_on") for s in item.get("sources") or [] if s.get("checked_on")]
    return dates or ([item["added_on"]] if item.get("added_on") else [])


def progress_days(runs, evidence_items, plan_actions):
    """For each scored day after Day 1, whether it showed real progress, and the proof.

    Real progress is any of: a role open on both days gained fit; evidence that
    is verified or corroborated had a source checked since the last scored day;
    a plan action was finished, with evidence, since the last scored day.
    Returns (days, streak): streak is how many scored days in a row, up to the
    latest, showed real progress."""
    days = [{"date": runs[0]["run_date"], "start": True, "progress": False, "roles_up": 0, "evidence": [], "actions": []}]
    for prev, cur in zip(runs, runs[1:]):
        a, b = prev["run_date"], cur["run_date"]
        before = {r["role_id"]: r["fit"] for r in prev["roles"]}
        same_rules = prev.get("rubric_version") == cur.get("rubric_version")
        up = [r for r in cur["roles"] if same_rules and r["role_id"] in before and r["fit"] > before[r["role_id"]]]
        ev = sorted(e["id"] for e in evidence_items
                    if e.get("level") in CHECKED and any(a < d <= b for d in _checked_dates(e)))
        done = sorted(x["id"] for x in plan_actions if x.get("status") == "done" and x.get("done_evidence")
                      and a < (x.get("finished_on") or "") <= b)
        days.append({"date": b, "start": False, "progress": bool(up or ev or done), "roles_up": len(up),
                     "evidence": ev, "actions": done})
    streak = 0
    for d in reversed(days[1:]):
        if not d["progress"]:
            break
        streak += 1
    return days, streak
