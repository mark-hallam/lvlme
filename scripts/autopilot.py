#!/usr/bin/env python3
"""Autopilot: record the person's answers, give the scheduler its prompt, and write the weekly note.

The skill skills/lvlme-autopilot asks the person first; this script only
records what they said yes to, and never changes the schedule on its own.

Usage
  python3 scripts/autopilot.py status
  python3 scripts/autopilot.py on --rhythm weekly --day mon --time 07:00 --run light \\
                                  --sources github,website --helpers yes --scheduler desktop_task
  python3 scripts/autopilot.py off
  python3 scripts/autopilot.py prompt          # the scheduled task's prompt (also saved to campaign/autopilot-prompt.md)
  python3 scripts/autopilot.py schedule-line   # a crontab line, for a computer without the desktop app
  python3 scripts/autopilot.py week [--date YYYY-MM-DD]   # write this week's note, then rebuild the dashboard
Every command takes --workspace PATH.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _autopilot as A  # noqa: E402

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_REL = ("campaign", "autopilot-prompt.md")


def save_config(ws, config):
    C.write_json(C.wpath(ws, "config.json"), config)


def turn_on(ws, config, args, today):
    ap = {"enabled": True, "rhythm": args.rhythm, "time": args.time, "run": args.run,
          "sources": [s.strip() for s in (args.sources or "").split(",") if s.strip() and s.strip().lower() != "none"],
          "helpers": args.helpers == "yes", "scheduler": args.scheduler, "approved_on": today}
    if args.rhythm == "weekly":
        ap["day"] = args.day
    config["autopilot"] = ap
    save_config(ws, config)
    C.write_text(C.wpath(ws, *PROMPT_REL), A.task_prompt(ENGINE, ws, A.settings(config)))
    return A.settings(config)


def describe(ap, today):
    if not ap.get("enabled"):
        return "Autopilot is off." + (" Turned off on %s." % ap["turned_off_on"] if ap.get("turned_off_on") else "")
    return ("Autopilot is on: %s, a %s run. Approved sources: %s. Helper agents: %s. Next run: %s." % (
        A.when_text(ap), ap["run"], ", ".join(ap["sources"]) or "workspace files only",
        "yes" if ap["helpers"] else "no (new scores above 2 wait for review)", A.next_run(ap, today)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="LVLme Autopilot: settings, schedule and the weekly note.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    on = sub.add_parser("on", help="record the person's yes")
    on.add_argument("--rhythm", choices=["weekly", "daily"], default="weekly")
    on.add_argument("--day", choices=A.DAYS, default="mon")
    on.add_argument("--time", default="07:00")
    on.add_argument("--run", choices=["light", "full"], default="light")
    on.add_argument("--sources", default="")
    on.add_argument("--helpers", choices=["yes", "no"], default="yes")
    on.add_argument("--scheduler", choices=["desktop_task", "cron", "launchd", "other"], default="desktop_task")
    for name in ("off", "status", "prompt", "schedule-line"):
        sub.add_parser(name)
    for name in ("on", "off", "status"):
        sub.choices[name].add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    wk = sub.add_parser("week")
    wk.add_argument("--date")
    wk.add_argument("--no-dashboard", action="store_true", help="write the note only")
    for p in sub.choices.values():
        p.add_argument("--workspace", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if getattr(args, "date", None) else C.today_in(config)
    if args.cmd == "on":
        if not re.match(r"^[0-2][0-9]:[0-5][0-9]$", args.time):
            raise SystemExit("lvlme: the time must be HH:MM, for example 07:00.")
        s = turn_on(ws, config, args, today)
        print(describe(s, today))
        print("Saved the scheduled task's prompt to %s. Set up the schedule now (skills/lvlme-autopilot)."
              % os.path.join(*PROMPT_REL))
    elif args.cmd == "off":
        config["autopilot"] = dict(config.get("autopilot") or {}, enabled=False, turned_off_on=today)
        save_config(ws, config)
        print("Autopilot is off. Also turn off the scheduled task itself (skills/lvlme-autopilot says how).")
    elif args.cmd == "status":
        print(describe(A.settings(config), today))
        note = A.newest_note(ws)
        print("Latest note: %s." % note["date"] if note else "No weekly note yet.")
    elif args.cmd == "prompt":
        text = A.task_prompt(ENGINE, ws, A.settings(config))
        C.write_text(C.wpath(ws, *PROMPT_REL), text)
        print(text, end="")
    elif args.cmd == "schedule-line":
        s = A.settings(config)
        prompt = C.wpath(ws, *PROMPT_REL)
        C.write_text(prompt, A.task_prompt(ENGINE, ws, s))
        print(A.cron_line(ENGINE, ws, s, prompt, C.wpath(ws, "campaign", "autopilot.log")))
    else:
        note = A.write_note(ws, config, today)
        if not args.no_dashboard:
            import build_dashboard as B
            with open(os.devnull, "w") as quiet:
                old, sys.stdout = sys.stdout, quiet
                try:
                    B.main(["--workspace", ws])
                finally:
                    sys.stdout = old
        print("Wrote campaign/weekly/%s.json. The one thing to do this week: %s" % (
            note["date"], note["action"]["title"] if note["action"] else "nothing new: keep going with the plan."))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
