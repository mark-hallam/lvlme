#!/usr/bin/env python3
"""Find doors: events, programmes and communities where people from the target organisations can be met.

Reads each public Luma calendar the person named in config.json (doors.calendars,
its iCal feed address), keeps events from today to doors.horizon_days ahead that
name a target organisation or are near the person's home city, adds fellowship,
residency and ambassador postings already in market/roles/latest.json, and
merges them into market/doors.json. A door the person has already marked keeps
its status, plan action and notes. See scripts/_doors.py.

Never fetched, whatever the config says: Meetup and Eventbrite pages and
LinkedIn. A calendar that fails is recorded and the others carry on. Read only:
nothing is registered, RSVPed, applied for or paid.

Usage
  python3 scripts/fetch_doors.py [--workspace PATH] [--date YYYY-MM-DD]
  python3 scripts/fetch_doors.py --ics saved.ics [--ics more.ics]   # read saved calendar files, no network
  python3 scripts/fetch_doors.py --offline                          # job-board programmes only, no network
"""
import argparse
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _doors as DR  # noqa: E402

UA = "lvlme/0.6 (personal job-search research script: public event calendars; read only)"


def fetch_text(url, timeout=45):
    """GET one calendar. Refuses Meetup, Eventbrite and LinkedIn addresses, and anything not https."""
    if DR.blocked(url):
        raise RuntimeError("LVLme never fetches %s (its terms forbid it, or LVLme never opens it)" % DR.host_of(url))
    if not url.lower().startswith("https://"):
        raise RuntimeError("only https:// calendar addresses are read")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/calendar, text/plain"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("%s: %s" % (type(exc).__name__, exc))


def calendars_of(config, ics_files):
    if ics_files:
        return [{"url": "file:" + os.path.basename(p), "path": p} for p in ics_files]
    return list(((config.get("doors") or {}).get("calendars")) or [])


def collect(ws, config, today, ics_files=(), offline=False):
    """(found doors, notes per calendar) from the calendars and the fetched job boards."""
    tz = (config.get("candidate") or {}).get("timezone") or "UTC"
    horizon = (config.get("doors") or {}).get("horizon_days") or DR.HORIZON_DAYS
    found, notes = [], {}
    for cal in [] if offline and not ics_files else calendars_of(config, ics_files):
        try:
            text = C.read_input(cal["path"], "calendar file") if cal.get("path") else fetch_text(cal["url"])
            doors = DR.from_ical(DR.parse_ics(text, tz), cal, config, today, horizon)
            if cal.get("path"):
                for d in doors:
                    d["source"] = d["link"] if d["link"] != cal["url"] else d["source"]
            found += doors
            notes[cal.get("name") or cal["url"]] = "%d door%s" % (len(doors), "" if len(doors) == 1 else "s")
        except RuntimeError as exc:
            notes[cal.get("name") or cal["url"]] = "skipped: %s" % exc
    roles = C.load_json(C.wpath(ws, "market", "roles", "latest.json"), None)
    programmes = DR.from_roles(roles, config)
    if programmes:
        notes["job boards"] = "%d programme%s" % (len(programmes), "" if len(programmes) == 1 else "s")
    return found + programmes, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find events, programmes and communities at the target organisations.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    ap.add_argument("--ics", action="append", default=[], help="a saved iCal file to read instead of the network")
    ap.add_argument("--offline", action="store_true", help="no network: job-board programmes only")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    found, notes = collect(ws, config, today, args.ics, args.offline)
    doc, added, refreshed = DR.merge(C.load_json(C.wpath(ws, DR.REL), None), found, today)
    C.write_json(C.wpath(ws, DR.REL), doc)
    print("Doors: %d new, %d already known, %d upcoming in %s." % (
        added, refreshed, len(DR.upcoming(doc, today)), DR.REL))
    for name, note in notes.items():
        print("  %s: %s" % (name, note))
    if not notes:
        print("  No calendars in config.json (doors.calendars) and no programmes on the job boards. Add a public "
              "Luma calendar's iCal address, or add a door by hand with scripts/doors.py add.")
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
