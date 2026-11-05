#!/usr/bin/env python3
"""Build the proof profile: a clean page of the claims you have checked, each with its public source.

Private by default: the page is written to report/profile/index.html in your workspace and goes nowhere
until you choose to host it (docs/PROOF-PROFILE.md). Only evidence at verified or corroborated level,
with at least one public https source, is shown. If the page would contain an email address, a phone
number, a folder path from your computer, a private or local link, or a claim below corroborated, nothing
is written and the reason is printed.

Usage
  python3 scripts/proof_profile.py --workspace PATH [--date YYYY-MM-DD] [--json]
Writes report/profile/index.html and report/profile/profile.json (the same facts for agents).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _proof_profile as PP  # noqa: E402

OUT = ("report", "profile")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the proof profile from checked evidence.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--date", help="the date to stamp on the page, YYYY-MM-DD (default: today)")
    ap.add_argument("--json", action="store_true", help="print a summary as JSON")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    model = PP.build_model(ws, config, today)
    page = PP.render(model)
    problems = PP.leak_problems(page, model["redact_terms"])
    if problems:
        print("lvlme: the proof profile was not written, because " + "; and ".join(problems) + ". "
              "Fix it in profile/evidence.json or config.json, then run this again. Any earlier page was left as it was.",
              file=sys.stderr)
        return 1
    facts = {"name": model["name"], "goal": model["goal"], "built_on": today, "levels": model["levels"],
             "claims": model["claims"], "checked_claims_without_public_link": model["held_back"]}
    C.write_text(C.wpath(ws, *OUT, "index.html"), page)
    C.write_json(C.wpath(ws, *OUT, "profile.json"), facts)
    summary = {"wrote": ["report/profile/index.html", "report/profile/profile.json"], "claims_shown": len(model["claims"]),
               "checked_claims_without_public_link": model["held_back"], "private_by_default": True}
    print(json.dumps(summary, indent=2) if args.json else
          "Wrote report/profile/index.html: %d checked claims shown. It stays private until you choose to host it."
          % len(model["claims"]))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
