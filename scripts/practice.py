#!/usr/bin/env python3
"""Practise before an interview, debrief after it: a question set for one role, and the bank of questions asked.

Before: `questions` prints a practice set for one role, with the person's
stories that fit each question. The agent asks them one at a time and gives
feedback on structure (situation, task, action, result) and evidence, citing
the stories; never a script to memorise, and never during a live interview.
After: `record` saves each question, rated strong, solid or gap. A real
interview's question (--real --app) also moves that application to Interview
if it was earlier, with a line in the application log. See scripts/_practice.py.

Usage
  python3 scripts/practice.py questions --role acme:4100001 [--json]
  python3 scripts/practice.py record --question TEXT --rating gap [--theme impact] [--story S01 ...]
                                     [--real --app ap4] [--org acme] [--note TEXT]
  python3 scripts/practice.py list [--json]
Every command takes --workspace PATH and --date YYYY-MM-DD.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _practice as PR  # noqa: E402
import _stories as ST  # noqa: E402
import applications as APC  # noqa: E402


def load(ws, *rel, default=None):
    return C.load_json(C.wpath(ws, *rel), None) or default


def find_role(ws, role_id):
    roles = load(ws, "market", "roles", "latest.json", default={}).get("roles") or []
    role = next((r for r in roles if r.get("id") == role_id), None)
    if role is None:
        raise SystemExit("lvlme: no open role %s in market/roles/latest.json. Pick one from the dashboard's Roles."
                         % role_id)
    return role


def record(ws, config, args, today):
    bank = load(ws, *PR.REL.split("/"), default=PR.empty())
    stories = {s["id"] for s in load(ws, *ST.REL.split("/"), default=ST.empty())["stories"]}
    for s in args.story:
        if s not in stories:
            raise SystemExit("lvlme: no story %s in %s." % (s, ST.REL))
    if args.theme and args.theme not in {t["id"] for t in ST.themes(config)}:
        raise SystemExit("lvlme: %r is not a story theme." % args.theme)
    q = {"id": PR.next_id(bank), "text": args.question, "kind": "real" if args.real else "practice",
         "rating": args.rating, "asked_on": today, "stories": args.story}
    for key in ("theme", "org", "note"):
        if getattr(args, key):
            q[key] = getattr(args, key)
    moved = None
    if args.app:
        doc = APC.load(ws)
        app = APC.find(doc, args.app)
        q["app"], q["org"] = app["id"], app["org"]
        if args.real and app["stage"] in ("applied", "responded", "assessment"):
            moved = app["stage"]
            APC.move(ws, doc, app, "interview", today, "from a debrief")
    elif args.real and not args.org:
        raise SystemExit("lvlme: a real interview question needs --app (or at least --org).")
    bank["questions"].append(q)
    bank["updated_on"] = max(bank.get("updated_on") or today, today)
    C.write_json(C.wpath(ws, PR.REL), bank)
    return q, moved


def main(argv=None):
    ap = argparse.ArgumentParser(description="Practise before an interview, debrief after it (never during).")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("questions", help="a practice set for one role")
    q.add_argument("--role", required=True)
    q.add_argument("--json", action="store_true")
    r = sub.add_parser("record", help="save a question asked, in practice or for real, with its rating")
    r.add_argument("--question", required=True)
    r.add_argument("--rating", required=True, choices=PR.RATINGS)
    r.add_argument("--theme")
    r.add_argument("--story", nargs="*", default=[], help="story ids used in the answer")
    r.add_argument("--real", action="store_true", help="asked in a real interview (a debrief)")
    r.add_argument("--app", help="the application it was for")
    r.add_argument("--org")
    r.add_argument("--note", default="")
    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    for p in (q, r, ls):
        p.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
        p.add_argument("--workspace", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    if args.cmd == "questions":
        role = find_role(ws, args.role)
        org_name = C.target_names(config).get(role.get("org"), role.get("org"))
        qs = PR.questions_for(role, org_name, load(ws, *ST.REL.split("/")), load(ws, *PR.REL.split("/")), config,
                              load(ws, "profile", "evidence.json"))
        if args.json:
            print(json.dumps(qs, indent=2, ensure_ascii=False))
            return 0
        print("Practice set: %s, %s. %s" % (role["title"], org_name, PR.NOTE))
        for i, x in enumerate(qs, 1):
            print("%d. %s\n   %s Stories that fit: %s." % (i, x["text"], x["why"], ", ".join(x["stories"]) or
                                                          "none yet (a gap worth a story)"))
    elif args.cmd == "record":
        x, moved = record(ws, config, args, today)
        print("Saved %s (%s, %s)%s." % (x["id"], x["kind"], x["rating"],
                                        "; %s moved from %s to Interview" % (x["app"], moved) if moved else ""))
    else:
        bank = load(ws, *PR.REL.split("/"), default=PR.empty())
        if args.json:
            print(json.dumps(bank["questions"], indent=2, ensure_ascii=False))
            return 0
        for x in bank["questions"]:
            print("%-4s %-8s %-6s %s" % (x["id"], x["kind"], x["rating"], x["text"]))
        if not bank["questions"]:
            print("No questions saved yet.")
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
