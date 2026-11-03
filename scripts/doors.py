#!/usr/bin/env python3
"""Doors: add one by hand, mark it, turn it into a plan action, or record who you met there.

Each change is one the person has confirmed: the agent asks first, then runs
the command. Nothing here registers, RSVPs, applies or pays; that is always
the person's own step. See scripts/_doors.py and scripts/fetch_doors.py.

Usage
  python3 scripts/doors.py add --kind event --title "AI meetup" --on 2026-11-12 [--time 18:00]
                               --place Melbourne --link URL --source URL [--source-kind employer_page]
                               [--org acme] [--closes YYYY-MM-DD] [--online] [--verified] [--note TEXT]
  python3 scripts/doors.py status DR03 going           # new, interested, going, went, applied, skipped
  python3 scripts/doors.py plan DR03 [--later]         # add it to campaign/plan.json as an action
  python3 scripts/doors.py met DR03 --org acme --person "Sam Lee" [--role "Product lead"]
  python3 scripts/doors.py list [--all] [--json]
Every command takes --workspace PATH and --date YYYY-MM-DD.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _doors as DR  # noqa: E402
import _warm_paths as W  # noqa: E402

PLAN = "campaign/plan.json"


def load(ws):
    return C.load_json(C.wpath(ws, DR.REL), None) or DR.empty()


def save(ws, doc, today):
    doc["updated_on"] = max(doc.get("updated_on") or today, today)
    C.write_json(C.wpath(ws, DR.REL), doc)


def find(doc, did):
    door = next((d for d in doc.get("doors") or [] if d.get("id") == did), None)
    if door is None:
        raise SystemExit("lvlme: no door %s in %s. Run `list --all` to see the ids." % (did, DR.REL))
    return door


def add(doc, args, config, today):
    targets = C.target_ids(config)
    for o in args.org:
        if o not in targets:
            raise SystemExit("lvlme: %r is not a target in config.json (targets: %s)." % (o, ", ".join(targets)))
    if args.kind not in ("programme", "community") and not args.on:
        raise SystemExit("lvlme: %s %s needs --on YYYY-MM-DD, the day it happens." % (
            "an" if args.kind == "event" else "a", args.kind))
    door = {"kind": args.kind, "title": args.title, "orgs": args.org, "place": args.place or ("Online" if args.online
            else ""), "online": args.online, "link": args.link, "source": args.source or args.link,
            "source_kind": args.source_kind, "verified": args.verified,
            "uid": "added:%s@%s" % (args.title, args.on or args.closes or today),
            "why": DR.why_of(args.kind, args.org, C.target_names(config), args.online)}
    for key, value in (("starts_on", args.on), ("time", args.time), ("closes_on", args.closes)):
        if value:
            if key == "time" and not re.match(r"^[0-2][0-9]:[0-5][0-9]$", value):
                raise SystemExit("lvlme: bad time %r, use HH:MM (24 hour)" % value)
            door[key] = C.check_date(value) if key != "time" else value
    if args.note:
        door["note"] = args.note
    doc, added, _ = DR.merge(doc, [door], today)
    if not added:
        raise SystemExit("lvlme: that door is already in %s (same link or title and date)." % DR.REL)
    return doc["doors"][-1]


def to_plan(ws, config, door, later, today):
    plan = C.load_json(C.wpath(ws, PLAN), None)
    if plan is None:
        raise SystemExit("lvlme: no %s yet. A door becomes an action once the campaign has a plan." % PLAN)
    if door.get("action") and any(a.get("id") == door["action"] for a in plan.get("actions") or []):
        raise SystemExit("lvlme: %s is already plan action %s." % (door["id"], door["action"]))
    roles = C.load_json(C.wpath(ws, "market", "roles", "latest.json"), None)
    action = DR.action_for(door, plan, config, roles, today)
    if later:
        action["status"] = "later"
    plan.setdefault("actions", []).append(action)
    plan["updated_on"] = max(plan.get("updated_on") or today, today)
    C.write_json(C.wpath(ws, PLAN), plan)
    door["action"] = action["id"]
    if door.get("status") == "new":
        door["status"] = "interested"
    return action


def met(ws, door, org, person, role, today):
    """The person names someone they met at the door: a warm-path contact at 'talked'. Never a guess."""
    if org not in (door.get("orgs") or [org]):
        raise SystemExit("lvlme: %s is about %s, not %s." % (door["id"], ", ".join(door["orgs"]), org))
    path = C.wpath(ws, W.REL)
    warm = C.load_json(path, None) or {"schema_version": 1, "contacts": []}
    if any(c.get("org") == org and c.get("person", "").lower() == person.lower() for c in warm["contacts"]):
        raise SystemExit("lvlme: %s at %s is already in %s. Move their stage there instead." % (person, org, W.REL))
    n = max([int(c["id"][1:]) for c in warm["contacts"] if re.match(r"^W\d+$", c.get("id", ""))] or [0]) + 1
    note = "Met at %s (%s)." % (door["title"], door["id"])
    contact = {"id": "W%02d" % n, "org": org, "person": person, "stage": "talked", "updated_on": today,
               "note": note, "history": [{"stage": "talked", "on": today, "note": note}]}
    if role:
        contact["role"] = role
    if door.get("action"):
        contact["action"] = door["action"]
    warm["contacts"].append(contact)
    warm["updated_on"] = max(warm.get("updated_on") or today, today)
    C.write_json(path, warm)
    if door.get("status") in ("new", "interested", "going"):
        door["status"] = "went"
    return contact


def show(doc, today, show_all, as_json):
    rows = (sorted(doc.get("doors") or [], key=lambda d: (DR.date_of(d) or "9999", d["id"])) if show_all
            else DR.upcoming(doc, today))
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        print("No upcoming doors. Run scripts/fetch_doors.py, or add one with `add`.")
    for d in rows:
        print("%-5s %-10s %-8s %s, %s, %s%s" % (
            d["id"], DR.KIND_NAMES.get(d["kind"]), DR.STATUS_NAMES.get(d.get("status", "new")), d["title"],
            DR.when_text(d), d.get("place") or "place not given", " (plan %s)" % d["action"] if d.get("action") else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Doors: events, programmes and communities (you register yourself).")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add a door the person or the lead found")
    a.add_argument("--kind", required=True, choices=DR.KINDS)
    a.add_argument("--title", required=True)
    a.add_argument("--link", required=True)
    a.add_argument("--source", help="where the facts come from (default: the link)")
    a.add_argument("--source-kind", default="person", choices=DR.SOURCE_KINDS)
    a.add_argument("--org", action="append", default=[], help="a target id; repeat for more")
    a.add_argument("--on", help="YYYY-MM-DD: the day it happens (events and conferences)")
    a.add_argument("--time", help="HH:MM, local")
    a.add_argument("--closes", help="YYYY-MM-DD: applications close (programmes)")
    a.add_argument("--place", default="")
    a.add_argument("--online", action="store_true")
    a.add_argument("--verified", action="store_true", help="the lead opened the source itself")
    a.add_argument("--note", default="")
    s = sub.add_parser("status")
    s.add_argument("id")
    s.add_argument("status", choices=DR.STATUSES)
    p = sub.add_parser("plan")
    p.add_argument("id")
    p.add_argument("--later", action="store_true", help="park it: off the active list until switched on")
    m = sub.add_parser("met")
    m.add_argument("id")
    m.add_argument("--org", required=True)
    m.add_argument("--person", required=True, help="their name, as the person gave it")
    m.add_argument("--role", default="")
    ls = sub.add_parser("list")
    ls.add_argument("--all", action="store_true")
    ls.add_argument("--json", action="store_true")
    for q in (a, s, p, m, ls):
        q.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    doc = load(ws)
    if args.cmd == "add":
        door = add(doc, args, config, today)
        save(ws, doc, today)
        print("Added %s: %s, %s." % (door["id"], door["title"], DR.when_text(door)))
        return 0
    if args.cmd == "list":
        show(doc, today, args.all, args.json)
        return 0
    door = find(doc, args.id)
    if args.cmd == "status":
        door["status"] = args.status
        print("%s is now %s." % (door["id"], DR.STATUS_NAMES[args.status]))
    elif args.cmd == "plan":
        action = to_plan(ws, config, door, args.later, today)
        print("Added plan action %s: %s (%s, about %s fit points per role on %d role%s if it works)." % (
            action["id"], action["title"], action["status"], action["expected_points"], action["roles_affected"],
            "" if action["roles_affected"] == 1 else "s"))
    else:
        contact = met(ws, door, args.org, args.person, args.role, today)
        print("Added %s to warm paths at Talked (%s). Progress only: it changes no score." % (contact["person"],
                                                                                          contact["id"]))
    save(ws, doc, today)
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
