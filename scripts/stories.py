#!/usr/bin/env python3
"""The interview story bank: record the person's stories, see the gaps, turn a gap into a plan action.

Each story is the person's own, in their words, recorded after they confirm
it: the agent asks first, then runs the command. LVLme never writes a story or
a number for them. See scripts/_stories.py for the themes and how a story's
strength is worked out.

Usage
  python3 scripts/stories.py add --title "Six-site rollout" --theme impact [--theme lead]
                                 --situation TEXT --task TEXT --action TEXT --result TEXT
                                 [--reflection TEXT] [--evidence E05 ...] [--source intake]
  python3 scripts/stories.py gaps [--json]           # themes with no story, or only your word
  python3 scripts/stories.py plan THEME [--later]    # add a gap to campaign/plan.json as an action
  python3 scripts/stories.py list [--json]
Every command takes --workspace PATH and --date YYYY-MM-DD.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _stories as ST  # noqa: E402

PLAN = "campaign/plan.json"


def load(ws):
    return C.load_json(C.wpath(ws, ST.REL), None) or ST.empty()


def save(ws, doc, today):
    doc["updated_on"] = max(doc.get("updated_on") or today, today)
    C.write_json(C.wpath(ws, ST.REL), doc)


def add(doc, args, config, evidence, today):
    known = {t["id"] for t in ST.themes(config)}
    for t in args.theme:
        if t not in known:
            raise SystemExit("lvlme: %r is not a story theme (themes: %s)." % (t, ", ".join(sorted(known))))
    ids = set(ST.levels_of(evidence))
    for e in args.evidence:
        if e not in ids:
            raise SystemExit("lvlme: %s is not in profile/evidence.json. Record the evidence first." % e)
    story = {"id": ST.next_id(doc), "title": args.title, "themes": args.theme, "situation": args.situation,
             "task": args.task, "action": args.action, "result": args.result, "evidence": args.evidence,
             "source": args.source, "added_on": today}
    if args.reflection:
        story["reflection"] = args.reflection
    doc.setdefault("stories", []).append(story)
    return story


def to_plan(ws, doc, config, evidence, theme, later, today):
    row = next((r for r in ST.coverage(doc, config, evidence) if r["id"] == theme), None)
    if row is None:
        raise SystemExit("lvlme: %r is not a story theme." % theme)
    if row["status"] == "backed":
        raise SystemExit("lvlme: \"%s\" already has a story backed by evidence." % row["name"])
    plan = C.load_json(C.wpath(ws, PLAN), None)
    if plan is None:
        raise SystemExit("lvlme: no %s yet. A gap becomes an action once the campaign has a plan." % PLAN)
    have = (doc.get("actions") or {}).get(theme)
    if have and any(a.get("id") == have for a in plan.get("actions") or []):
        raise SystemExit("lvlme: \"%s\" is already plan action %s." % (row["name"], have))
    action = ST.action_for(row, plan, config, today)
    if later:
        action["status"] = "later"
    plan.setdefault("actions", []).append(action)
    plan["updated_on"] = max(plan.get("updated_on") or today, today)
    C.write_json(C.wpath(ws, PLAN), plan)
    doc.setdefault("actions", {})[theme] = action["id"]
    return action


def main(argv=None):
    ap = argparse.ArgumentParser(description="Interview story bank: your stories, in your words.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="record a story the person told and confirmed")
    a.add_argument("--title", required=True)
    a.add_argument("--theme", action="append", default=[], required=True, help="a theme id; repeat for more")
    for key in ("situation", "task", "action", "result"):
        a.add_argument("--" + key, required=True)
    a.add_argument("--reflection", default="", help="what they would do differently")
    a.add_argument("--evidence", nargs="*", default=[], help="evidence ids that back it")
    a.add_argument("--source", default="person", choices=ST.SOURCES)
    p = sub.add_parser("plan")
    p.add_argument("theme")
    p.add_argument("--later", action="store_true")
    g = sub.add_parser("gaps")
    g.add_argument("--json", action="store_true")
    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    for q in (a, p, g, ls):
        q.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    doc, evidence = load(ws), C.load_json(C.wpath(ws, "profile", "evidence.json"), None)
    if args.cmd == "add":
        s = add(doc, args, config, evidence, today)
        save(ws, doc, today)
        print("Added %s: %s (%s)." % (s["id"], s["title"], ST.strength(s, ST.levels_of(evidence)).replace("_", " ")))
    elif args.cmd == "plan":
        action = to_plan(ws, doc, config, evidence, args.theme, args.later, today)
        save(ws, doc, today)
        print("Added plan action %s: %s (%s)." % (action["id"], action["title"], action["status"]))
    elif args.cmd == "gaps":
        rows = ST.gaps(doc, config, evidence)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        for r in [] if args.json else rows:
            print("%-13s %-16s %s" % (r["id"], ST.STATUS_NAMES[r["status"]], r["ask"]))
        if not rows and not args.json:
            print("Every theme has a story backed by evidence.")
    else:
        levels = ST.levels_of(evidence)
        rows = [dict(s, strength=ST.strength(s, levels)) for s in doc.get("stories") or []]
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        for s in [] if args.json else rows:
            print("%-4s %-22s %s (%s)" % (s["id"], s["strength"].replace("_", " "), s["title"], ", ".join(s["themes"])))
        if not rows and not args.json:
            print("No stories yet. Ask the person for one, then record it with `add`.")
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
