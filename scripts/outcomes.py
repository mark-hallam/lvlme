#!/usr/bin/env python3
"""Outcome opt-in: preview, build the consent page, or save the numbers-only export. Nothing is ever sent.

Usage
  python3 scripts/outcomes.py preview            print what would be shared (writes nothing)
  python3 scripts/outcomes.py page               write report/share-numbers.html (the consent screen), then rebuild the dashboard link
  python3 scripts/outcomes.py export --consent   write report/outcomes-export.json; refused without --consent
Every command takes --workspace PATH.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _outcomes as O  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="LVLme outcome opt-in: numbers only, your choice, nothing sent.")
    ap.add_argument("--workspace")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preview")
    sub.add_parser("page")
    ex = sub.add_parser("export")
    ex.add_argument("--consent", action="store_true", help="you have read what is in it and choose to save it")
    for p in sub.choices.values():
        p.add_argument("--workspace", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        p.add_argument("--date", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    ap.add_argument("--date")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if getattr(args, "date", None) else C.today_in(config)
    export = O.build(ws, today)
    if args.cmd == "preview":
        print(O.CONSENT + "\n\nIn it:\n- " + "\n- ".join(O.IN) + "\n\nNever in it:\n- " + "\n- ".join(O.NOT_IN) + "\n")
        print(json.dumps(export, indent=2))
    elif args.cmd == "page":
        C.write_text(C.wpath(ws, "report", "share-numbers.html"), O.page(export))
        print("Wrote report/share-numbers.html. Nothing was sent. Rebuild the dashboard to link it from Today.")
    else:
        if not args.consent:
            print("lvlme: not saved. Run `python3 scripts/outcomes.py preview` to see exactly what is in it, then add --consent "
                  "if you choose to save it. Nothing is ever sent.", file=sys.stderr)
            return 1
        C.write_json(C.wpath(ws, "report", "outcomes-export.json"), export)
        print("Saved report/outcomes-export.json (%d applications). LVLme sent nothing; sharing it is up to you." % export["applications"])
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
