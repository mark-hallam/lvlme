#!/usr/bin/env python3
"""Before a run: how many roles need judging, and about how many helper agents a full or a light run starts.

A full run can start dozens of helper agents, and people on a usage plan can
use up their limit without knowing. This prints the size of both kinds of run
so the person can pick, before anything starts. It never guesses a token or a
dollar figure: it counts roles and helpers, nothing else.

A role needs judging (requirements match, proof of work, organisation edge)
when any of these is true:
  - it has no judgement yet in eval/judgements.json;
  - the employer changed the posting after it was judged (the board's updated_at);
  - evidence that bears on those factors was added or checked after it was
    judged (an evidence item's added_on or a source's checked_on, for items
    on D1, D2 or D4 that are not scoped to another organisation).
Every other role keeps its last judgement, and the score says when it was judged.

Full run: every role that needs judging. Light run: of those, the top N by
fit in the newest run (default 30), plus every role never judged.

Helpers, as docs/ORCHESTRATION.md sizes them: one role judge per batch of
about 8 roles, about one blind reviewer per two judge batches (the reviewer
only sees scores above 2 and a few others), and, on a full run only, one
market scout per target organisation.

Usage
  python3 scripts/run_plan.py [--workspace PATH] [--top 30] [--json]
"""
import argparse
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

BATCH = 8
JUDGED = {"D1", "D2", "D4"}


def evidence_dates(evidence):
    """[(date, orgs or None)] for each evidence item on a judged factor: when it was added or last checked."""
    out = []
    for item in (evidence or {}).get("items") or []:
        if not JUDGED & set(item.get("dimensions") or []):
            continue
        dates = [item.get("added_on") or ""] + [s.get("checked_on") or "" for s in item.get("sources") or []]
        out.append((max(dates), set(item["orgs"]) if item.get("orgs") else None))
    return out


def why_judge(role, judgement, ev_dates):
    """Why a role needs judging, or None when its last judgement still stands."""
    judged = (judgement or {}).get("judged_on")
    if not judged:
        return "new"
    if (role.get("updated_at") or "")[:10] > judged:
        return "posting changed"
    if any(d > judged and (orgs is None or role.get("org") in orgs) for d, orgs in ev_dates):
        return "new evidence"
    return None


def last_fits(ws):
    runs = sorted(glob.glob(C.wpath(ws, "eval", "runs", "*.json")))
    run = (C.load_json(runs[-1], {}) or {}) if runs else {}
    return {r["role_id"]: r.get("fit", 0) for r in run.get("roles") or [] if r.get("judged", True)}


def helpers(n_roles, targets):
    judges = math.ceil(n_roles / BATCH)
    reviewers = math.ceil(judges / 2)
    return {"roles": n_roles, "judges": judges, "reviewers": reviewers, "scouts": targets,
            "helpers": judges + reviewers + targets}


def plan(ws, config, top=30):
    roles = (C.load_json(C.wpath(ws, "market", "roles", "latest.json"), {}) or {}).get("roles") or []
    judgements = (C.load_json(C.wpath(ws, "eval", "judgements.json"), {}) or {}).get("roles") or {}
    ev_dates = evidence_dates(C.load_json(C.wpath(ws, "profile", "evidence.json"), {}))
    fits = last_fits(ws)
    reasons = {r["id"]: why_judge(r, judgements.get(r["id"]), ev_dates) for r in roles}
    todo = [rid for rid, why in reasons.items() if why]
    ranked = sorted(todo, key=lambda rid: (-fits.get(rid, -1), rid))
    light = [rid for rid in ranked if rid in fits][:top] + [rid for rid in todo if reasons[rid] == "new"]
    light = list(dict.fromkeys(light))
    targets = len(C.target_ids(config))
    return {
        "open_roles": len(roles), "unchanged": len(roles) - len(todo),
        "reasons": {k: sum(1 for w in reasons.values() if w == k) for k in ("new", "posting changed", "new evidence")},
        "full": dict(helpers(len(todo), targets), role_ids=sorted(todo)),
        "light": dict(helpers(len(light), 0), role_ids=light, top=top),
    }


def n_of(n, one, many=None):
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def say(p):
    f, lt = p["full"], p["light"]
    kept = p["unchanged"]
    lines = ["%s open. %s." % (n_of(p["open_roles"], "role"),
                               "All of them need judging" if not kept else
                               "1 keeps its last judgement: nothing it depends on has changed" if kept == 1 else
                               "%d keep their last judgement: nothing they depend on has changed" % kept)]
    if not f["roles"]:
        lines.append("Nothing needs judging: this run starts no judging helpers.")
        return lines
    why = ", ".join("%d %s" % (n, k) for k, n in p["reasons"].items() if n)
    lines.append("Full run: judges %s (%s) with about %s: %s, about %s and %s." % (
        n_of(f["roles"], "role"), why, n_of(f["helpers"], "helper"), n_of(f["judges"], "judge"),
        n_of(f["reviewers"], "blind reviewer"), n_of(f["scouts"], "market scout")))
    if lt["roles"] < f["roles"]:
        lines.append("Light run: judges your top %d by fit, plus any new roles: %s with about %s. "
                     "The rest keep their last judgement." % (lt["top"], n_of(lt["roles"], "role"), n_of(lt["helpers"], "helper")))
    lines.append("Helper counts only: LVLme never guesses tokens or cost. You choose.")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="Size a full and a light run before it starts.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--top", type=int, default=30, help="roles in a light run, by last fit (default 30)")
    ap.add_argument("--json", action="store_true", help="print the plan, with the role ids for each run, as JSON")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    p = plan(ws, config, args.top)
    print(json.dumps(p, indent=2) if args.json else "\n".join(say(p)))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
