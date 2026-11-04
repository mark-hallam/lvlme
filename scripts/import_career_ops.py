#!/usr/bin/env python3
"""Import from career-ops: applications and their history, contacts at your targets, and interview stories.

For someone already using career-ops (github.com/career-ops-hq/career-ops):
LVLme reads their folder, read only, and adds what it finds, marked as
imported, so they keep both tools. The agent shows the --dry-run first and
runs the import after the person's yes. See scripts/_career_ops.py for the
formats.

  applications  -> campaign/applications.json (and its log), with career-ops'
                   tracker number in x_career_ops; its status history goes in
                   the log. Re-importing updates a changed stage, never adds
                   a second copy.
  contacts      -> campaign/warm-paths.json, only for your target
                   organisations, at stage talked (a contact entry shows an
                   exchange happened, not more; move them up yourself).
                   Name, company and title only: never phone, email or
                   LinkedIn.
  stories       -> profile/stories.json, source career-ops, matched to
                   LVLme's themes by their words; a story no theme matches is
                   listed for the person to place by hand.

Imported items are the person's own account until checked, like any CV line:
nothing here adds evidence or changes a score.

Usage
  python3 scripts/import_career_ops.py --from ~/career-ops --dry-run
  python3 scripts/import_career_ops.py --from ~/career-ops [--only applications contacts stories]
Takes --workspace PATH and --date YYYY-MM-DD.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _applications as AP  # noqa: E402
import _career_ops as CO  # noqa: E402
import _stories as ST  # noqa: E402
import _warm_paths as W  # noqa: E402
import applications as APC  # noqa: E402

PARTS = ("applications", "contacts", "stories")


def org_matcher(config):
    names = {}
    for t in config.get("targets") or []:
        for n in [t["id"], t.get("name")] + list(t.get("aliases") or []):
            if n:
                names[n.strip().lower()] = t["id"]
    return lambda company: names.get((company or "").strip().lower())


def import_applications(ws, src, match, today, dry):
    doc = APC.load(ws)
    known = {(a.get("x_career_ops") or {}).get("tracker"): a for a in doc["applications"]}
    added, moved = [], []
    for r in src["applications"]:
        if not r["stage"]:
            continue
        hist = src["log"].get(r["num"], [])
        last = hist[-1][0] if hist else r["date"] or today
        have = known.get(r["num"])
        if have:
            if have["stage"] != r["stage"]:
                moved.append((have["id"], have["stage"], r["stage"]))
                if not dry:
                    before = have["stage"]
                    have.update(stage=r["stage"], last_step_on=max(last, have["last_step_on"]), nudges=0)
                    APC.save(ws, doc, today, have, "stage", before, r["stage"], "from career-ops #%d" % r["num"])
            continue
        applied = next((d for d, _, to, _ in hist if to == "applied"), None)
        if not applied and r["stage"] not in ("evaluated", "skip", "discarded"):
            applied = r["date"] or None
        n = max([int(a["id"][2:]) for a in doc["applications"] if re.match(r"^ap\d+$", a.get("id", ""))] or [0]) + 1
        app = {"id": "ap%d" % n, "org": match(r["company"]) or r["company"], "title": r["role"], "stage": r["stage"],
               "last_step_on": max(last, applied or last), "nudges": 0,
               "notes": ("Imported from career-ops #%d. %s" % (r["num"], r["notes"])).strip(),
               "x_career_ops": {"tracker": r["num"], "score": r["score"], "status": r["status"]}}
        if applied:
            app["applied_on"] = applied
        if r["url"]:
            app["url"] = r["url"]
        added.append(app)
        if dry:
            continue
        doc["applications"].append(app)
        APC.save(ws, doc, today, app, "imported", "", r["stage"], "career-ops #%d" % r["num"])
        for date, before, to, source in hist:
            APC.save(ws, doc, date, app, "stage", before or "", to or "", "career-ops %s" % source)
    return added, moved


def import_contacts(ws, src, match, today, dry):
    path = C.wpath(ws, W.REL)
    warm = C.load_json(path, None) or {"schema_version": 1, "contacts": []}
    have = {(c.get("org"), c.get("person", "").lower()) for c in warm["contacts"]}
    added, skipped = [], 0
    for c in src["contacts"]:
        org = match(c["company"])
        if not org:
            skipped += 1
            continue
        if (org, c["name"].lower()) in have:
            continue
        n = max([int(x["id"][1:]) for x in warm["contacts"] if re.match(r"^W\d+$", x.get("id", ""))] or [0]) + 1
        note = "Imported from career-ops%s." % (" (%s)" % c["type"] if c["type"] else "")
        contact = {"id": "W%02d" % n, "org": org, "person": c["name"], "stage": "talked", "updated_on": today,
                   "note": note, "history": [{"stage": "talked", "on": today, "note": note}]}
        if c["title"]:
            contact["role"] = c["title"]
        warm["contacts"].append(contact)
        have.add((org, c["name"].lower()))
        added.append(contact)
    if added and not dry:
        warm["updated_on"] = max(warm.get("updated_on") or today, today)
        C.write_json(path, warm)
    return added, skipped


def import_stories(ws, src, config, today, dry):
    path = C.wpath(ws, ST.REL)
    doc = C.load_json(path, None) or ST.empty()
    known, titles = {t["id"] for t in ST.themes(config)}, {s["title"].lower() for s in doc["stories"]}
    added, unplaced = [], []
    for s in src["stories"]:
        if s["title"].lower() in titles:
            continue
        themes = CO.themes_for(s, known)
        if not themes or not all(s.get(k) for k in ("situation", "task", "result")):
            unplaced.append(s["title"])
            continue
        story = {"id": ST.next_id(doc), "title": s["title"], "themes": themes, "situation": s["situation"],
                 "task": s["task"], "action": s["action"], "result": s["result"], "evidence": [],
                 "source": "career-ops", "added_on": today, "x_career_ops": {"theme": s.get("theme", "")}}
        if s.get("reflection"):
            story["reflection"] = s["reflection"]
        doc["stories"].append(story)
        titles.add(s["title"].lower())
        added.append(story)
    if added and not dry:
        doc["updated_on"] = max(doc.get("updated_on") or today, today)
        C.write_json(path, doc)
    return added, unplaced


def main(argv=None):
    ap = argparse.ArgumentParser(description="Import from a career-ops folder (read only).")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--from", dest="src", required=True, help="the career-ops folder")
    ap.add_argument("--only", nargs="+", choices=PARTS, default=list(PARTS))
    ap.add_argument("--dry-run", action="store_true", help="show what would be imported; write nothing")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    src, match = CO.read_folder(os.path.expanduser(args.src)), org_matcher(config)
    lead = "Would import" if args.dry_run else "Imported"
    if "applications" in args.only:
        added, moved = import_applications(ws, src, match, today, args.dry_run)
        print("%s %d application%s from career-ops; %d already here changed stage." % (
            lead, len(added), "" if len(added) == 1 else "s", len(moved)))
        for a in added:
            print("  %s, %s: %s" % (a["title"], a["org"], AP.STAGE_NAMES[a["stage"]]))
    if "contacts" in args.only:
        added, skipped = import_contacts(ws, src, match, today, args.dry_run)
        print("%s %d contact%s at your targets into warm paths, at Talked (name and title only); %d at other "
              "companies left out." % (lead, len(added), "" if len(added) == 1 else "s", skipped))
    if "stories" in args.only:
        added, unplaced = import_stories(ws, src, config, today, args.dry_run)
        print("%s %d stor%s into the story bank, as your word until backed by evidence." % (
            lead, len(added), "y" if len(added) == 1 else "ies"))
        for t in unplaced:
            print("  Not placed (no theme matched, or a STAR part missing): %s. Add it with stories.py add." % t)
    if args.dry_run:
        print("Nothing written. Run again without --dry-run once the person says yes.")
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
