#!/usr/bin/env python3
"""Build in public: ideas worth sharing, a draft brief in your voice, and the record of what you posted.

LVLme plans and drafts; the person posts, under their own name. Each change is
one the person confirmed: the agent asks first, then runs the command. See
scripts/_public.py.

Usage
  python3 scripts/public.py ideas [--json]                 # what you finished that is worth sharing
  python3 scripts/public.py draft A03 [--channel x]        # a draft brief in campaign/drafts/ for one idea
  python3 scripts/public.py posted P01 --url URL [--channel x]   # the person posted it
  python3 scripts/public.py checked P01                    # the agent opened the link and it shows the post
  python3 scripts/public.py result P01 --note "3 replies, 1 new contact"
  python3 scripts/public.py skip P01
  python3 scripts/public.py list [--json]
Every command takes --workspace PATH and --date YYYY-MM-DD.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _public as PB  # noqa: E402

EVIDENCE = "profile/evidence.json"


def load(ws, *rel, default=None):
    return C.load_json(C.wpath(ws, *rel), None) or default


def save(ws, doc, today):
    doc["updated_on"] = max(doc.get("updated_on") or today, today)
    C.write_json(C.wpath(ws, PB.REL), doc)


def find(doc, pid):
    post = next((p for p in doc["posts"] if p.get("id") == pid), None)
    if post is None:
        raise SystemExit("lvlme: no post %s in %s. Run `list` to see the ids." % (pid, PB.REL))
    return post


def facts_for(idea, plan, evidence_doc, doors_doc):
    """Only checked, written-down facts about the idea, so a draft never adds a claim."""
    out = [idea["title"] + "."]
    for a in (plan or {}).get("actions") or []:
        if a["id"] == idea["ref"]:
            out += [x for x in ("Done when: " + a.get("done_when", ""), a.get("done_evidence") and
                                "Shown by: %s" % a["done_evidence"]) if x and not x.endswith(": ")]
    ev = {e["id"]: e for e in (evidence_doc or {}).get("items") or []}
    if idea["ref"] in ev:
        e = ev[idea["ref"]]
        out += ["Level: %s." % e["level"].replace("_", " ")] + ["Source: %s" % s["ref"] for s in e.get("sources") or []]
    for d in (doors_doc or {}).get("doors") or []:
        if d["id"] == idea["ref"]:
            out += ["%s, %s." % (d["title"], d.get("place") or "place not given"), "Link: %s" % d.get("link")]
    return out


def draft(ws, config, doc, ref, channel, today):
    plan, evidence, doors = load(ws, "campaign", "plan.json"), load(ws, EVIDENCE), load(ws, "market", "doors.json")
    idea = next((i for i in PB.ideas(plan, evidence, doors, None, today) if i["ref"] == ref), None)
    if idea is None:
        raise SystemExit("lvlme: %s is not a current idea. Run `ideas` to see them." % ref)
    if ref in PB.used_refs(doc):
        raise SystemExit("lvlme: %s already has a post in %s." % (ref, PB.REL))
    post = {"id": PB.next_id(doc), "about": ref, "title": idea["title"], "channel": channel, "status": "drafted",
            "drafted_on": today}
    rel = "campaign/drafts/public-%s-%s.md" % (post["id"], today)
    C.write_text(C.wpath(ws, *rel.split("/")), PB.brief(post, idea, config, facts_for(idea, plan, evidence, doors)))
    post["draft_file"] = rel
    doc["posts"].append(post)
    return post


def checked(ws, post, today):
    """The agent opened the post's link and it shows the post: a verified public_signal evidence item."""
    if post.get("status") != "posted" or not post.get("url"):
        raise SystemExit("lvlme: %s has no posted link yet. Record it with `posted --url` first." % post["id"])
    if post.get("evidence"):
        raise SystemExit("lvlme: %s is already evidence %s." % (post["id"], post["evidence"]))
    path = C.wpath(ws, EVIDENCE)
    ev = C.load_json(path, None) or {"schema_version": 1, "items": []}
    n = max([int(e["id"][1:]) for e in ev["items"] if re.match(r"^E\d+$", e.get("id", ""))] or [0]) + 1
    item = {"id": "E%02d" % n, "claim": "Public post on %s: %s" % (PB.CHANNEL_NAMES.get(post["channel"]), post["title"]),
            "kind": "public_signal", "level": "verified", "dimensions": ["D5"],
            "sources": [{"type": "website", "ref": post["url"], "checked_on": today}], "added_on": today,
            "notes": "Build in public post %s, opened and checked." % post["id"]}
    ev["items"].append(item)
    C.write_json(path, ev)
    post["evidence"] = item["id"]
    return item


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build in public: LVLme drafts, you post.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ideas")
    i.add_argument("--json", action="store_true")
    d = sub.add_parser("draft")
    d.add_argument("ref", help="an idea's ref: a plan action, an evidence id or a door id")
    d.add_argument("--channel", choices=PB.CHANNELS)
    p = sub.add_parser("posted")
    p.add_argument("id")
    p.add_argument("--url", required=True)
    p.add_argument("--channel", choices=PB.CHANNELS)
    c = sub.add_parser("checked")
    c.add_argument("id")
    r = sub.add_parser("result")
    r.add_argument("id")
    r.add_argument("--note", required=True, help="what it led to, in plain words")
    s = sub.add_parser("skip")
    s.add_argument("id")
    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    for q in (i, d, p, c, r, s, ls):
        q.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
        q.add_argument("--workspace", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    doc = load(ws, *PB.REL.split("/"), default=PB.empty())
    if args.cmd == "ideas":
        found = PB.ideas(load(ws, "campaign", "plan.json"), load(ws, EVIDENCE), load(ws, "market", "doors.json"),
                         doc, today)
        if args.json:
            print(json.dumps(found, indent=2, ensure_ascii=False))
        for x in [] if args.json else found:
            print("%-5s %s. %s" % (x["ref"], x["title"], x["why"]))
        if not found and not args.json:
            print("Nothing new to share from the last %d days. Finish a proof action, then share it." % PB.LOOKBACK_DAYS)
        return 0
    if args.cmd == "list":
        if args.json:
            print(json.dumps(doc["posts"], indent=2, ensure_ascii=False))
        for x in [] if args.json else doc["posts"]:
            print("%-4s %-8s %-9s %s%s" % (x["id"], x["status"], PB.CHANNEL_NAMES.get(x["channel"], ""), x["title"],
                                          " (%s)" % x["url"] if x.get("url") else ""))
        return 0
    if args.cmd == "draft":
        post = draft(ws, config, doc, args.ref, args.channel or PB.settings(config)["channels"][0], today)
        print("Draft brief written: %s. Fill in the notes with the person, draft in their voice, and they post it."
              % post["draft_file"])
    else:
        post = find(doc, args.id)
        if args.cmd == "posted":
            post.update(status="posted", posted_on=today, url=args.url)
            if args.channel:
                post["channel"] = args.channel
            print("Recorded %s as posted on %s. Open the link, then run `checked %s`." % (post["id"], today, post["id"]))
        elif args.cmd == "checked":
            item = checked(ws, post, today)
            print("Added %s: a verified public signal. The next run can judge it." % item["id"])
        elif args.cmd == "result":
            post["result"] = args.note
            print("Saved what %s led to." % post["id"])
        else:
            post["status"] = "skipped"
            print("%s skipped: its idea is free to come back." % post["id"])
    save(ws, doc, today)
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
