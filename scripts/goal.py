#!/usr/bin/env python3
"""Test the goal against the starting line, choose a stepping stone, and set the next goal.

Usage
  python3 scripts/goal.py check [--json]           test the goal; saves campaign/goal-check.json
  python3 scripts/goal.py startline [--json]       the starting line in plain words
  python3 scripts/goal.py stone accept|decline     the person's choice on the proposed stepping stone
  python3 scripts/goal.py next-goal --role R [--organisations "A, B"] [--where W] [--by YYYY-MM-DD]
                                                   keep the goal just ended in goal_history, start the next
Every command takes --workspace PATH.

The stepping stone is only ever a proposal. Nothing in config.json changes until
the person says accept, and declining is remembered so Today stops asking.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _goal as G  # noqa: E402

CHECK_REL = ("campaign", "goal-check.json")


def build_page(ws, config, today=None):
    import build_dashboard as B
    data = B.Data(ws, config, today)
    return B.build_data(data), data


def do_check(ws, config, today):
    page, data = build_page(ws, config, today)
    goal = config.get("goal") or {}
    result = G.check(page, goal, page["meta"]["run_date"])
    result["checked_on"] = data.today
    result["decision"] = None
    old = C.load_json(C.wpath(ws, *CHECK_REL), None) or {}
    if old.get("stepping_stone") == result.get("stepping_stone") and old.get("decision"):
        result["decision"] = old["decision"]          # the person has already answered this same proposal
    C.write_json(C.wpath(ws, *CHECK_REL), result)
    return result


def text_of(result):
    lines = [result["text"]]
    stone = result.get("stepping_stone")
    if stone:
        lines += ["", "A stepping stone to consider: %s." % stone["title"], stone["why"], "",
                  "You choose. To take it: python3 scripts/goal.py stone accept. To keep your goal as it is: "
                  "python3 scripts/goal.py stone decline."]
    return "\n".join(lines)


def do_stone(ws, config, choice, today):
    saved = C.load_json(C.wpath(ws, *CHECK_REL), None)
    stone = (saved or {}).get("stepping_stone")
    if not stone:
        raise SystemExit("lvlme: there is no stepping stone to choose. Run scripts/goal.py check first.")
    saved["decision"] = "accepted" if choice == "accept" else "declined"
    saved["decided_on"] = today
    if choice == "accept":
        config["goal"]["stepping_stone"] = dict(stone, accepted_on=today)
        C.write_json(C.wpath(ws, "config.json"), config)
    C.write_json(C.wpath(ws, *CHECK_REL), saved)
    return ("Stepping stone saved in config.json. Your goal is unchanged; the stone comes first." if choice == "accept"
            else "Kept your goal as it is. LVLme will not suggest this stone again.")


def do_next_goal(ws, config, args, today):
    goal = config.get("goal") or {}
    if not (args.role or "").strip():
        raise SystemExit("lvlme: say the next role with --role.")
    history = config.setdefault("goal_history", [])
    history.append(dict({k: v for k, v in goal.items() if k not in ("description",)},
                        ended_on=today, outcome=args.outcome))
    orgs = [o.strip() for o in (args.organisations or "").split(",") if o.strip()]
    new = {"slug": G_slug(args.role, orgs), "role": args.role.strip(), "started_on": today,
           "title": G.goal_sentence(args.role, orgs, args.where, args.by)}
    new["description"] = new["title"]
    if orgs:
        new["organisations"] = orgs
    if (args.where or "").strip():
        new["where"] = args.where.strip()
    if args.by:
        new["by"] = C.check_date(args.by)
    config["goal"] = new
    C.write_json(C.wpath(ws, "config.json"), config)
    if os.path.exists(C.wpath(ws, *CHECK_REL)):
        os.remove(C.wpath(ws, *CHECK_REL))
    return "Next goal set: %s. The last one is kept in goal_history in config.json." % new["title"]


def G_slug(role, orgs):
    import init
    return init.slugify(" ".join([role] + orgs))


def main(argv=None):
    ap = argparse.ArgumentParser(description="LVLme goal: test it, choose a stepping stone, set the next one.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "startline"):
        sub.add_parser(name).add_argument("--json", action="store_true")
    st = sub.add_parser("stone")
    st.add_argument("choice", choices=["accept", "decline"])
    ng = sub.add_parser("next-goal")
    ng.add_argument("--role", required=True)
    ng.add_argument("--organisations")
    ng.add_argument("--where")
    ng.add_argument("--by")
    ng.add_argument("--outcome", default="reached", choices=["reached", "replaced", "dropped"])
    for p in sub.choices.values():
        p.add_argument("--workspace", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        p.add_argument("--date", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if getattr(args, "date", None) else C.today_in(config)
    if args.cmd == "check":
        result = do_check(ws, config, today)
        print(json.dumps(result, indent=2) if args.json else text_of(result))
    elif args.cmd == "startline":
        page, data = build_page(ws, config, today)
        line = G.starting_line(page, page["meta"]["run_date"])
        if args.json:
            print(json.dumps(line, indent=2))
        else:
            print(_startline_text(line))
    elif args.cmd == "stone":
        print(do_stone(ws, config, args.choice, today))
    else:
        print(do_next_goal(ws, config, args, today))
    return 0


def _startline_text(line):
    if not line:
        return "No role has been judged yet, so there is no starting line yet."
    head = "Level %d, %s: %s for your best match." % (line["level"], line["band"], line["fit_text"])
    if not line["has_range"]:
        head += " (One judging so far: a range appears when each role is judged twice.)"
    return head + "\n" + line["next"]


if __name__ == "__main__":
    sys.exit(C.run_main(main))
