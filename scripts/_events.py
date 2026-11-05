"""Level events: a level-up and a goal reached, recorded in eval/levels.json.

eval/levels.json holds {"schema_version": 1, "events": [...]}; each event is
{date, kind: "level_up" | "goal_reached", from_level, to_level, role_id, evidence: [ids]}.
The events come from the scored runs: the level is the fit band of the best judged role that day, and an event is
recorded only when the level rose between two runs scored under the same rules (a change of rubric version is never
called a level-up). evidence lists the ids of the plan actions finished with evidence and the evidence items checked
in the period that led to it (_levels.progress_days). A goal is reached when the best fit first reaches the goal's
level (default Level 4, Good).

Events are only ever added: running the dashboard again never rewrites or drops one, even if an old run file is later
deleted. The share card built from an event shows the level and the dates and no names of organisations or people.
No network calls.
"""
import datetime as dt

import _common as C
import _goal as G
import _levels as L

REL = ("eval", "levels.json")


def _best_role(run):
    best = None
    for r in run.get("roles") or []:
        if r.get("judged", True) and r.get("fit") is not None and (best is None or r["fit"] > best["fit"]):
            best = r
    return best


def detect(runs, progress_days, goal):
    """Events found in the scored runs (oldest first), best judged role each day."""
    events, prev, prev_run = [], None, None
    days = {d["date"]: d for d in progress_days}
    tl = G.target_level(goal)
    reached = False
    for run in runs:
        best = _best_role(run)
        if best is None:
            continue
        lv = L.band_index(best["fit"]) + 1
        comparable = prev_run is not None and prev_run.get("rubric_version") == run.get("rubric_version")
        if prev is not None and comparable and lv > prev:
            p = days.get(run["run_date"]) or {}
            events.append({"date": run["run_date"], "kind": "level_up", "from_level": prev, "to_level": lv,
                           "role_id": best["role_id"], "evidence": sorted(set((p.get("evidence") or []) + (p.get("actions") or [])))})
        if lv >= tl and not reached:
            reached = True
            if prev is None or comparable:
                p = days.get(run["run_date"]) or {}
                events.append({"date": run["run_date"], "kind": "goal_reached", "from_level": prev or lv, "to_level": lv,
                               "role_id": best["role_id"], "outcome": "reached",
                               "evidence": sorted(set((p.get("evidence") or []) + (p.get("actions") or [])))})
        prev, prev_run = lv, run
    return events


def key(e):
    return (e["kind"], e["date"], e["to_level"])


def merged(existing, runs, progress_days, goal):
    """The recorded events plus any the runs show that are not recorded yet, oldest first. Never drops one."""
    have = {key(e) for e in existing or []}
    new = [e for e in detect(runs, progress_days, goal) if key(e) not in have]
    return sorted(list(existing or []) + new, key=lambda e: (e["date"], e["kind"])), bool(new)


def load(ws):
    return (C.load_json(C.wpath(ws, *REL), None) or {}).get("events") or []


def update(ws, runs, progress_days, goal):
    """Add any new events to eval/levels.json (never remove one). Returns all the events, oldest first."""
    events, changed = merged(load(ws), runs, progress_days, goal)
    if changed:
        C.write_json(C.wpath(ws, *REL), {"schema_version": 1, "events": events})
    return events


def recent(events, today, kind, days=21):
    """The newest event of this kind within the last `days` days, or None."""
    found = [e for e in events if e["kind"] == kind and 0 <= (dt.date.fromisoformat(today) - dt.date.fromisoformat(e["date"])).days <= days]
    return max(found, key=lambda e: e["date"]) if found else None


def share_card(event, start_date, band_names=C.BANDS):
    """What the level-up share card says: level and dates only, no names of organisations or people."""
    to, frm = event["to_level"], event["from_level"]
    days = (dt.date.fromisoformat(event["date"]) - dt.date.fromisoformat(start_date)).days
    if event["kind"] == "goal_reached":
        head = "Goal reached: Level %d, %s" % (to, band_names[to - 1])
    else:
        head = "Levelled up: Level %d, %s to Level %d, %s" % (frm, band_names[frm - 1], to, band_names[to - 1])
    line = ("Reached on %s, %d days after the first measurement on %s." % (G.long_date(event["date"]), days, G.long_date(start_date))
            if days > 0 else "Measured on %s." % G.long_date(event["date"]))
    return {"head": head, "line": line, "level": to, "date": event["date"], "start": start_date}
