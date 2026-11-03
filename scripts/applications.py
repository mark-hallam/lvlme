#!/usr/bin/env python3
"""Track applications and their follow-ups: campaign/applications.json, with an append-only log.

Every change is one the person has confirmed: the agent asks first, then runs
the command. Each change also adds one line to campaign/applications-log.tsv
(date, id, event, from, to, note), which is never edited. Progress only:
score.py never reads either file. Drafts only: `draft` writes a note for the
person to finish and send; nothing is ever sent. See scripts/_applications.py
for the follow-up timing.

Usage
  python3 scripts/applications.py add --org anthropic --title "Applied AI Architect" [--role-id ID] [--url URL]
                                      [--stage applied] [--date YYYY-MM-DD] [--note TEXT]
  python3 scripts/applications.py move ap1 interview [--date YYYY-MM-DD] [--note TEXT]
  python3 scripts/applications.py followup ap1 [--date YYYY-MM-DD]   # the person sent a follow-up
  python3 scripts/applications.py thanks ap1 [--date YYYY-MM-DD]     # the person sent a thank-you note
  python3 scripts/applications.py draft ap1                          # write the due note to campaign/drafts/
  python3 scripts/applications.py list [--json]
Every command takes --workspace PATH.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _applications as AP  # noqa: E402
import _first_draft as FD  # noqa: E402


def load(ws):
    return C.load_json(C.wpath(ws, AP.REL), None) or {"schema_version": 1, "applications": []}


def save(ws, doc, date, app, event, before, after, note=""):
    doc["updated_on"] = max(doc.get("updated_on") or date, date)
    C.write_json(C.wpath(ws, AP.REL), doc)
    path, clean = C.wpath(ws, AP.LOG), lambda s: re.sub(r"[\t\r\n]+", " ", str(s or "")).strip()
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write("date\tid\tevent\tfrom\tto\tnote\n")
        f.write("\t".join(clean(x) for x in (date, app["id"], event, before, after, note)) + "\n")


def find(doc, aid):
    app = next((a for a in doc["applications"] if a.get("id") == aid), None)
    if app is None:
        raise SystemExit("lvlme: no application %s in %s. Run `list` to see the ids." % (aid, AP.REL))
    return app


def add(ws, doc, args, date):
    n = max([int(a["id"][2:]) for a in doc["applications"] if re.match(r"^ap\d+$", a.get("id", ""))] or [0]) + 1
    app = {"id": "ap%d" % n, "org": args.org, "title": args.title, "stage": args.stage, "last_step_on": date, "nudges": 0}
    for key in ("role_id", "url"):
        if getattr(args, key):
            app[key] = getattr(args, key)
    if args.stage == "applied":
        app["applied_on"] = date
    if args.note:
        app["notes"] = args.note
    doc["applications"].append(app)
    save(ws, doc, date, app, "added", "", args.stage, args.note)
    return app


def move(ws, doc, app, stage, date, note):
    before = app["stage"]
    app.update(stage=stage, last_step_on=date, nudges=0, thanked=False)
    if stage == "applied" and not app.get("applied_on"):
        app["applied_on"] = date
    save(ws, doc, date, app, "stage", before, stage, note)


def sent(ws, doc, app, kind, date):
    f = AP.follow_up(app, date)
    if kind == "thanks":
        if app.get("stage") != "interview":
            raise SystemExit("lvlme: %s is at %s; a thank-you note follows an interview." % (app["id"], app["stage"]))
        app["thanked"] = True
    else:
        if app.get("stage") not in AP.CHASED or (app.get("nudges") or 0) >= AP.MAX_NUDGES:
            raise SystemExit("lvlme: no follow-up is due for %s (%s). At most %d per stage, then let it go quiet."
                             % (app["id"], AP.STAGE_NAMES.get(app["stage"]), AP.MAX_NUDGES))
        app["nudges"] = (app.get("nudges") or 0) + 1
        app["last_step_on"] = date
    save(ws, doc, date, app, kind, f["status"], "sent", "")


def draft(ws, config, app, date):
    """A note for the person to finish and send: the facts, and a gap for their own words."""
    f = AP.follow_up(app, date)
    if not f["what"]:
        raise SystemExit("lvlme: nothing is due for %s (%s)." % (app["id"], AP.STAGE_NAMES.get(app["stage"])))
    names = C.target_names(config)
    org = names.get(app["org"], app["org"])
    policy = FD.first_draft_targets(config).get(app["org"], (None, None))[1]
    head = ("LVLme outreach. Policy: %s, checked %s.\n\n" % (policy["source"], policy.get("checked_on") or date)
            if policy else "")
    thanks = f["what"].startswith("Thank")
    body = [
        "# %s: %s, %s" % (f["what"], app["title"], org), "", head + "Draft only. Finish it in your own words, then send "
        "it yourself. Tell your agent when it is sent, so the tracker records it.", "",
        "- The role: %s%s" % (app["title"], " (%s)" % app["url"] if app.get("url") else ""),
        "- Applied on %s; last step %s (%s)." % (app.get("applied_on") or "not recorded", app["last_step_on"],
                                                 AP.STAGE_NAMES.get(app["stage"])),
        "- %s, due %s." % (f["what"], f["due_on"]), "",
        "Subject: %s" % ("Thank you: " + app["title"] if thanks else app["title"] + ": following up"), "",
        "Hi [name],", "",
        "[Your words: %s]" % ("thank them for their time, and name one thing from the conversation that made you "
                              "keener" if thanks else "say you are still keen, and add one new thing since you "
                              "applied, if there is one"), "",
        "[Your name]", ""]
    path = C.wpath(ws, "campaign", "drafts", "followup-%s-%s-%s.md" % (app["id"], app["org"], date))
    C.write_text(path, "\n".join(body))
    return path


def show(doc, date, as_json):
    rows = [dict(a, follow_up=AP.follow_up(a, date)) for a in AP.ordered(doc, date)]
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        print("No applications tracked yet. Add one with `add --org ... --title ...`.")
    for r in rows:
        f = r["follow_up"]
        print("%-5s %-12s %s, %s. Last step %s (%d day%s ago)%s" % (
            r["id"], AP.STAGE_NAMES.get(r["stage"]), r["title"], r["org"], r["last_step_on"], f["since"],
            "" if f["since"] == 1 else "s",
            ". %s: %s, %s" % (AP.LABELS[f["status"]], f["what"], f["due_on"]) if f["what"] and f["status"] != "waiting"
            else ". " + AP.LABELS[f["status"]] if f["status"] != "none" else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Track applications and follow-ups (drafts only; you send).")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add an application the person confirmed")
    a.add_argument("--org", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--role-id")
    a.add_argument("--url")
    a.add_argument("--stage", default="applied", choices=AP.STAGES)
    for name in ("move", "followup", "thanks", "draft"):
        p = sub.add_parser(name)
        p.add_argument("id")
        if name == "move":
            p.add_argument("stage", choices=AP.STAGES)
    for p in [a] + [sub.choices[n] for n in ("move", "followup", "thanks", "draft")]:
        p.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    for p in (a, sub.choices["move"]):
        p.add_argument("--note", default="")
    sub.add_parser("list").add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    date = C.check_date(args.date) if getattr(args, "date", None) else C.today_in(config)
    doc = load(ws)
    if args.cmd == "add":
        app = add(ws, doc, args, date)
        print("Added %s: %s, %s (%s)." % (app["id"], app["title"], app["org"], AP.STAGE_NAMES[app["stage"]]))
    elif args.cmd == "move":
        app = find(doc, args.id)
        move(ws, doc, app, args.stage, date, args.note)
        print("%s is now at %s." % (app["id"], AP.STAGE_NAMES[args.stage]))
    elif args.cmd in ("followup", "thanks"):
        app = find(doc, args.id)
        sent(ws, doc, app, args.cmd, date)
        print("Recorded: %s sent for %s." % ("thank-you note" if args.cmd == "thanks" else "follow-up", app["id"]))
    elif args.cmd == "draft":
        path = draft(ws, config, find(doc, args.id), date)
        print("Draft written: %s. The person finishes and sends it." % os.path.relpath(path, ws))
    else:
        show(doc, date, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
