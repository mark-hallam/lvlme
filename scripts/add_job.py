#!/usr/bin/env python3
"""Add one job posting to the campaign by link or pasted text.

Reads the posting the same way as scripts/quick_posting.py (public job board APIs,
JobPosting structured data on other pages, or pasted text). Classifies it with the
workspace config.json (role families, heavy coding, eligibility blockers), then
appends it to market/roles/manual.json for a manual target. Run fetch_roles.py
afterward to merge it into market/roles/latest.json.

Only fields read from the posting are saved (title, locations, pay, dates, URL,
department, remote). Nothing is applied or submitted.

Usage
  python3 scripts/add_job.py --workspace PATH --url URL [--org TARGET_ID] [--saved FILE]
  python3 scripts/add_job.py --workspace PATH --text-file FILE [--org TARGET_ID] [--title TITLE] [--url URL]
Every command takes --workspace PATH. --org must be a target whose ats is manual
(when omitted, the employer name must match a manual target's name or alias).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import fetch_roles as FR  # noqa: E402
import quick_posting as Q  # noqa: E402

MANUAL = ("market", "roles", "manual.json")


def manual_targets(config):
    return [t for t in config.get("targets") or [] if t.get("ats") == "manual"]


def resolve_target(config, org_id, employer_name):
    """Return the manual target for org_id, or match employer_name to one manual target."""
    by_id = {t["id"]: t for t in config.get("targets") or []}
    if org_id:
        if org_id not in by_id:
            raise SystemExit("lvlme: %r is not a target in config.json (targets: %s)." % (
                org_id, ", ".join(sorted(by_id))))
        target = by_id[org_id]
        if target.get("ats") != "manual":
            raise SystemExit("lvlme: target %r uses %s, not manual. add_job saves to market/roles/manual.json; "
                             "pick a manual target with --org, or add the employer's job board to config.json "
                             "and run fetch_roles.py instead." % (org_id, target.get("ats")))
        return target
    name = (employer_name or "").strip().lower()
    if not name:
        raise SystemExit("lvlme: could not tell which organisation this posting belongs to. "
                         "Give --org with a manual target id from config.json.")
    matches = []
    for t in manual_targets(config):
        names = [t.get("name") or ""] + list(t.get("aliases") or [])
        if any(n.strip().lower() == name for n in names if n):
            matches.append(t)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit("lvlme: employer name %r matches more than one manual target (%s). Use --org."
                         % (employer_name, ", ".join(t["id"] for t in matches)))
    manual = manual_targets(config)
    if not manual:
        raise SystemExit("lvlme: config.json has no manual target. Add one (ats manual) for employers whose "
                         "careers site LVLme does not read, then run this again.")
    raise SystemExit("lvlme: employer name %r does not match a manual target (%s). Use --org."
                     % (employer_name, ", ".join(t["id"] for t in manual)))


def build_role(config, target, base):
    role, reason = FR.build_role(target, base, config)
    if role is None:
        raise SystemExit("lvlme: this posting is not kept for scoring (%s). "
                         "Check config.json role families, or paste a different posting." % (reason or "unknown"))
    return Q.check_text(role)


def posting_entry(role):
    """One manual.json posting from a classified role (no invented fields)."""
    entry = {
        "org": role["org"],
        "id": role["id"].split(":", 1)[1],
        "title": role["title"],
        "locations": list(role.get("locations") or []),
        "description": role.get("description_text") or "",
    }
    if role.get("url"):
        entry["url"] = role["url"]
    if role.get("compensation"):
        entry["compensation"] = role["compensation"]
    if role.get("team_or_department"):
        entry["department"] = role["team_or_department"]
    if role.get("remote") is True:
        entry["remote"] = True
    for key in ("published_at", "updated_at"):
        if role.get(key):
            entry[key] = role[key]
    return entry


def merge_posting(doc, entry):
    postings = list((doc or {}).get("postings") or [])
    key = (entry["org"], entry["id"])
    postings = [p for p in postings if (p.get("org"), p.get("id")) != key]
    postings.append(entry)
    return {"postings": postings}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Add one job to market/roles/manual.json (read only).")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="the posting link")
    src.add_argument("--text-file", help="a file with the posting text ('-' reads standard input)")
    ap.add_argument("--org", help="manual target id from config.json")
    ap.add_argument("--title", help="role title when using --text-file (default: first line of the file)")
    ap.add_argument("--saved", help="offline: read this saved page or API response instead of the network")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    if C.setup_problem(config):
        print(C.setup_problem(config), file=sys.stderr)
        return 1
    try:
        if args.text_file:
            text = C.read_input(args.text_file, "posting text file")
            if args.org:
                target = resolve_target(config, args.org, None)
            else:
                preview = Q.base_from_text(text, args.title, None, args.url)
                target = resolve_target(config, None, preview.get("org_name"))
            base = Q.base_from_text(text, args.title, target.get("name"), args.url)
            source = {"kind": "text", "org_name": base.get("org_name")}
        else:
            base, source, _link = Q.fetch_base(args.url, args.saved)
            target = resolve_target(config, args.org, base.get("org_name") or source.get("org_name"))
    except Q.PostingError as exc:
        print("lvlme: %s" % exc, file=sys.stderr)
        return 3
    role = build_role(config, target, base)
    path = C.wpath(ws, *MANUAL)
    doc = C.load_json(path, {"postings": []})
    entry = posting_entry(role)
    C.write_json(path, merge_posting(doc, entry))
    out = {
        "role_id": role["id"],
        "title": role["title"],
        "org": role["org"],
        "requires_heavy_coding": role["requires_heavy_coding"],
        "coding_signals": role.get("coding_signals") or [],
        "eligibility_blockers": role.get("eligibility_blockers") or [],
        "manual_posting": entry,
        "source": source,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
