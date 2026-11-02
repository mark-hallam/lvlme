#!/usr/bin/env python3
"""Map the person's LinkedIn connections onto the target organisations.

Reads the Connections.csv file from LinkedIn's official "Get a copy of your
data" export (columns: First Name, Last Name, URL, Email Address, Company,
Position, Connected On) and writes profile/network.json: first-degree contacts
per target org, with position and how long connected.

Privacy: email addresses are never copied. Names stay in the workspace; this
script prints counts only. Second-degree paths and the per-contact fields
knows_my_work and note (added by the agent or the person) are kept on re-run.

Usage
  python3 scripts/network_map.py --workspace PATH --csv intake/sources/Connections.csv
  python3 scripts/network_map.py --csv PATH --today 2026-11-01
A relative --csv path is looked up from the current folder first, then inside the workspace.
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

LEGAL_SUFFIXES = {"inc", "incorporated", "llc", "ltd", "limited", "pty", "pbc", "corp", "corporation",
                  "co", "company", "gmbh", "plc", "lp", "llp", "ag", "sa", "bv", "the"}
DATE_FORMATS = ("%d %b %Y", "%d %B %Y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%b %d, %Y", "%d/%m/%Y")


def normalise(name):
    """Lower case, punctuation removed, legal suffixes dropped: 'OpenAI, Inc.' -> 'openai'."""
    words = re.sub(r"[^a-z0-9& ]+", " ", (name or "").lower().replace("&", " & ")).split()
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    while words and words[0] == "the":
        words.pop(0)
    return " ".join(words)


def org_matcher(config):
    """Return a function company -> target id or None, using names and aliases."""
    keys = []
    for t in config.get("targets", []):
        for alias in [t.get("name") or ""] + list(t.get("aliases") or []):
            n = normalise(alias)
            if n:
                keys.append((n, t["id"]))
    keys.sort(key=lambda k: -len(k[0]))  # longest alias first

    def match(company):
        c = normalise(company)
        if not c:
            return None
        for alias, tid in keys:
            if c == alias or (len(alias) >= 4 and c.startswith(alias + " ")):
                return tid
        return None
    return match


def parse_date(text):
    text = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def months_between(start, end):
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def read_connections(path):
    """Rows of the Connections.csv export, skipping LinkedIn's 'Notes' preamble."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise SystemExit("climb: cannot read %s (%s). Download your LinkedIn data "
                         "export and pass the path to its Connections.csv." % (path, exc.strerror))
    start = next((i for i, line in enumerate(lines) if "First Name" in line and "Company" in line), None)
    if start is None:
        raise SystemExit("climb: %s does not look like a LinkedIn Connections.csv "
                         "(no header row with First Name and Company)" % path)
    return list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))


def build_network(rows, config, today, previous=None, source=""):
    match = org_matcher(config)
    prev_orgs = (previous or {}).get("orgs") or {}
    kept = {}  # (org, name, company) -> fields the agent or person added
    for org, data in prev_orgs.items():
        for c in data.get("first_degree", []):
            extra = {k: c[k] for k in ("knows_my_work", "note") if k in c}
            if extra:
                kept[(org, c.get("name"), c.get("company"))] = extra
    orgs = {tid: {"count": 0, "first_degree": []} for tid in C.target_ids(config)}
    matched = 0
    for row in rows:
        company = (row.get("Company") or "").strip()
        tid = match(company)
        if not tid:
            continue
        name = " ".join(p for p in ((row.get("First Name") or "").strip(), (row.get("Last Name") or "").strip()) if p)
        on = parse_date(row.get("Connected On"))
        contact = {
            "name": name or "(name hidden in export)",
            "position": (row.get("Position") or "").strip(),
            "company": company,
            "connected_on": on.isoformat() if on else None,
            "months_connected": months_between(on, today) if on else None,
            "profile_url": (row.get("URL") or "").strip(),
        }
        contact.update(kept.get((tid, contact["name"], company), {}))
        orgs[tid]["first_degree"].append(contact)
        matched += 1
    for data in orgs.values():
        data["first_degree"].sort(key=lambda c: (-(c["months_connected"] or 0), c["name"]))
        data["count"] = len(data["first_degree"])
    return {
        "schema_version": 1,
        "generated_on": today.isoformat(),
        "source": source,
        "total_connections": len(rows),
        "matched_connections": matched,
        "orgs": orgs,
        "second_degree": list((previous or {}).get("second_degree") or []),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Map LinkedIn connections onto the target organisations.")
    ap.add_argument("--workspace", help="workspace folder (default: $CLIMB_HOME)")
    ap.add_argument("--csv", required=True, help="path to Connections.csv from the LinkedIn data export")
    ap.add_argument("--today", help="date to measure 'months connected' from (default: today)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = dt.date.fromisoformat(C.check_date(args.today) if args.today else C.today_in(config))
    csv_path = args.csv
    if not os.path.exists(csv_path) and os.path.exists(C.wpath(ws, csv_path)):
        csv_path = C.wpath(ws, csv_path)  # a path relative to the workspace, such as intake/sources/Connections.csv
    args.csv = csv_path
    rows = read_connections(args.csv)
    out_path = C.wpath(ws, "profile", "network.json")
    previous = C.load_json(out_path, None)
    full = os.path.abspath(args.csv)
    src = os.path.relpath(full, ws) if full.startswith(ws.rstrip(os.sep) + os.sep) else os.path.basename(full)
    network = build_network(rows, config, today, previous, source=src)
    C.write_json(out_path, network)
    print(json.dumps({"wrote": "profile/network.json", "total_connections": network["total_connections"],
                      "matched_connections": network["matched_connections"],
                      "first_degree_per_org": {k: v["count"] for k, v in network["orgs"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
