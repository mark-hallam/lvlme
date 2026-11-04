#!/usr/bin/env python3
"""Offer help: the posting's advertised pay range beside the offer, and a checklist of what to ask.

Rare for a reach job, but when an offer comes it matters. For one application
at Interview or Offer, it writes campaign/drafts/offer-<id>-<date>.md: the pay
range the posting advertised (from market/roles/latest.json, which LVLme read
from the job board), what the person says they were offered (their words, as
given), and questions to ask the employer and a lawyer before signing.

A checklist only. Figures come only from the posting or the person; nothing is
worked out or guessed. It never says an offer is fair or safe to sign, and it
gives no legal, tax or financial advice. The file stays in the private
workspace; sensitive mode keeps pay out of the files written for other agents.
No network calls here.

Usage
  python3 scripts/offer.py ap4 [--offered "AUD 165,000 base plus super"] [--date YYYY-MM-DD] [--workspace PATH]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import applications as APC  # noqa: E402

ASK_EMPLOYER = [
    "The base pay, and whether retirement contributions (superannuation in Australia) are on top or included.",
    "Any bonus: how it is decided, and what was paid last year.",
    "Any equity: how much, the vesting schedule and cliff, and what happens if you leave.",
    "Start date, location, and how many days in an office.",
    "Relocation or visa support, if you need either, in writing.",
    "Probation length, and the notice period on both sides.",
    "Leave, parental leave and other benefits.",
    "When they need your answer, and whether there is room to talk about any part of it.",
]
ASK_LAWYER = [
    "Restraint of trade or non-compete clauses: how long, how wide, and whether they hold where you live.",
    "Intellectual property: what you make in your own time, and side projects.",
    "Termination, and anything that ties you in (repaying a bonus or relocation).",
    "Anything in the written contract that differs from what you were told.",
]
NOTE = ("A checklist, not advice. LVLme never says an offer is fair or safe to sign. Figures here come only from "
        "the posting and from you; for the contract, ask a lawyer.")


def role_of(ws, app):
    roles = (C.load_json(C.wpath(ws, "market", "roles", "latest.json"), None) or {})
    return next((r for r in roles.get("roles") or [] if r.get("id") == app.get("role_id")), None), roles.get("fetched_on")


def brief(app, role, fetched_on, offered, org_name, today):
    if role and role.get("compensation"):
        pay = "Advertised in the posting: %s (%s, read from the job board on %s)." % (
            role["compensation"], role.get("url") or "the posting", fetched_on)
    elif role:
        pay = "The posting does not publish a pay range."
    else:
        pay = ("The posting is no longer in market/roles/latest.json, so its pay range cannot be shown. If you saved "
               "a copy of the posting, check it there.")
    lines = ["# Offer checklist: %s, %s" % (app["title"], org_name), "", NOTE, "",
             "## Pay", "", "- " + pay,
             "- What you were offered, in your words: %s" % (offered or "[not given yet]"), "",
             "## Ask the employer", ""] + ["- [ ] " + q for q in ASK_EMPLOYER] + [
             "", "## Ask a lawyer before you sign", ""] + ["- [ ] " + q for q in ASK_LAWYER] + [
             "", "## Your notes", "", "[What matters most to you in this offer, in your own words.]", "",
             "Written %s for application %s (stage: %s)." % (today, app["id"], app["stage"]), ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Offer help: the advertised pay range and a checklist (not advice).")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("id", help="the application, from scripts/applications.py list")
    ap.add_argument("--offered", default="", help="what the person says they were offered, in their words")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in the person's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.check_date(args.date) if args.date else C.today_in(config)
    app = APC.find(APC.load(ws), args.id)
    if app["stage"] not in ("interview", "offer"):
        raise SystemExit("lvlme: %s is at %s. Offer help is for an application at Interview or Offer."
                         % (app["id"], app["stage"]))
    role, fetched_on = role_of(ws, app)
    name = C.target_names(config).get(app["org"], app["org"])
    rel = "campaign/drafts/offer-%s-%s.md" % (app["id"], today)
    C.write_text(C.wpath(ws, *rel.split("/")), brief(app, role, fetched_on, args.offered, name, today))
    print("Offer checklist written: %s. %s" % (rel, NOTE))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
