"""Proof: how right has LVLme been for you? Its odds, set against what happened to the applications sent.

For each application sent, the bands LVLme gave that role on the day it was
sent: the latest scored run (eval/runs/) on or before applied_on. They are
frozen into the application as `predicted` when it is recorded, so a later run
never rewrites what was predicted. What happened comes from the stages the
person confirmed (campaign/applications.json and its append-only log).

    interview   yes once it reached interview, offer or hired; no if rejected
                before that, or if nothing has happened for QUIET_DAYS
    offer       yes once it reached offer or hired; no if rejected at any stage,
                or quiet before an interview; otherwise still waiting
    withdrawn   discarded by the person: left out, it says nothing about the odds

A band's real rate is shown only once it has MIN_BAND results, and the ranking
check only after MIN_RANK. Beside the person's own results sit public figures
(BASE): what a cold or referred application usually leads to. The blended rate
mixes them like PRIOR_WEIGHT imaginary past results (a Beta prior), so a few
results move it a little and many move it a lot.

Advisory only: score.py never reads this, and nothing here changes a score or a
band. A change to the bands would be a new rubric version (method/RUBRIC.md).
No network calls here.
"""
import glob
import html
import os

import _applications as AP
import _common as C

QUIET_DAYS = 60
MIN_BAND, MIN_RANK, PRIOR_WEIGHT = 5, 10, 10
WARM_D3 = 4   # the rubric's warm referral: D3 at least 4
SOURCE = {"name": "Ashby Talent Trends: referrals", "date": "16 May 2025",
          "url": "https://www.ashbyhq.com/talent-trends-report/reports/referrals",
          "about": "over 38 million applications across 93,000 jobs, 2021 to 2024"}
# Application to interview, and interview to offer: inbound (cold) and referred, from SOURCE.
BASE = {"cold": {"interview": 0.03, "offer_if_interview": 0.06},
        "referred": {"interview": 0.40, "offer_if_interview": 0.16}}
KINDS = ("interview", "offer")
NOTE = ("Advisory only: this checks LVLme's odds against what happened. It never changes a score; a change to the "
        "bands would be a new rubric version.")


def base_rate(kind, warm):
    b = BASE["referred" if warm else "cold"]
    return b["interview"] if kind == "interview" else b["interview"] * b["offer_if_interview"]


def load_runs(ws):
    """[(run_date, {role_id: role})], oldest first."""
    out = []
    for f in sorted(glob.glob(C.wpath(ws, "eval", "runs", "*.json"))):
        run = C.load_json(f, None) or {}
        if run.get("run_date"):
            out.append((run["run_date"], {r["role_id"]: r for r in run.get("roles") or [] if r.get("role_id")}))
    return out


def predicted(runs, role_id, on):
    """What LVLme said about role_id on date `on`: the latest run on or before it that scored the role, or None."""
    for run_date, roles in reversed(runs):
        if run_date <= on and role_id in roles:
            r = roles[role_id]
            return {"run_date": run_date, "fit": r.get("fit"), "interview_band": r.get("interview_band"),
                    "offer_band": r.get("offer_band"),
                    "warm": ((r.get("scores") or {}).get("D3") or {}).get("score", 0) >= WARM_D3}
    return None


def reached(ws):
    """{application id: set of stages it has been at}, from campaign/applications-log.tsv."""
    out = {}
    path = C.wpath(ws, "campaign", "applications-log.tsv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f.read().splitlines()[1:]:
                cells = line.split("\t")
                if len(cells) >= 5 and cells[2] in ("added", "stage", "imported"):
                    out.setdefault(cells[1], set()).add(cells[4])
    return out


def outcome(app, stages, today):
    """{"interview": True/False/None, "offer": ...}; None is still waiting. None overall if not sent or withdrawn."""
    stage = app.get("stage")
    if not app.get("applied_on") or stage in ("discarded", "skip", "evaluated"):
        return None
    seen = set(stages or ()) | {stage}
    quiet = stage in ("applied", "responded", "assessment") and AP.days(app.get("last_step_on"), today) >= QUIET_DAYS
    interview = True if seen & {"interview", "offer", "hired"} else False if stage == "rejected" or quiet else None
    offer = True if seen & {"offer", "hired"} else False if stage == "rejected" or interview is False else None
    return {"interview": interview, "offer": offer}


def results(ws, doc, today, runs=None):
    """One row per application sent: its prediction and what happened. Skips applications with no prediction."""
    runs = load_runs(ws) if runs is None else runs
    stages, rows, unmatched = reached(ws), [], 0
    for a in (doc or {}).get("applications") or []:
        out = outcome(a, stages.get(a.get("id")), today)
        if out is None:
            continue
        pred = a.get("predicted") or (predicted(runs, a["role_id"], a["applied_on"]) if a.get("role_id") else None)
        if not pred:
            unmatched += 1
            continue
        rows.append({"id": a["id"], "pred": pred, "out": out})
    return rows, unmatched


def ranking(rows, kind):
    """How often LVLme rated an application that got the result above one that didn't (ties count half), or None."""
    key = kind + "_band"
    done = [(C.CHANCE_BANDS.index(r["pred"][key]), r["out"][kind]) for r in rows
            if r["out"][kind] is not None and r["pred"].get(key) in C.CHANCE_BANDS]
    yes, no = [b for b, o in done if o], [b for b, o in done if not o]
    if len(done) < MIN_RANK or not yes or not no:
        return None
    pairs = [(1.0 if y > n else 0.5 if y == n else 0.0) for y in yes for n in no]
    return {"results": len(done), "share": round(sum(pairs) / len(pairs), 2)}


def summary(ws, doc, today, runs=None):
    """The panel's numbers, or None when no application has been sent yet."""
    rows, unmatched = results(ws, doc, today, runs)
    if not rows and not unmatched:
        return None
    out = {"note": NOTE, "source": SOURCE, "sent": len(rows), "unmatched": unmatched, "quiet_days": QUIET_DAYS,
           "min_band": MIN_BAND, "min_rank": MIN_RANK}
    for kind in KINDS:
        bands = []
        for band in C.CHANCE_BANDS:
            mine = [r for r in rows if r["pred"].get(kind + "_band") == band]
            if not mine:
                continue
            done = [r for r in mine if r["out"][kind] is not None]
            hits = sum(1 for r in done if r["out"][kind])
            expect = sum(base_rate(kind, r["pred"].get("warm")) for r in done)
            row = {"band": band, "sent": len(mine), "results": len(done), "hits": hits,
                   "waiting": len(mine) - len(done), "shown": len(done) >= MIN_BAND}
            if row["shown"]:
                prior = expect / len(done)
                row["rate"], row["public"] = round(hits / len(done), 3), round(prior, 4)
                row["blended"] = round((hits + PRIOR_WEIGHT * prior) / (len(done) + PRIOR_WEIGHT), 3)
            bands.append(row)
        out[kind] = {"bands": bands, "ranking": ranking(rows, kind)}
    return out


def pct(x):
    return "%d%%" % round(100 * x) if x >= 0.01 or x == 0 else "under 1%"


def band_line(kind, b):
    what = "an interview" if kind == "interview" else "an offer"
    head = "%s: %d sent, %d with a result" % (b["band"], b["sent"], b["results"])
    if not b["shown"]:
        return head + ". Your rate shows after %d results." % MIN_BAND
    return head + ". %d led to %s: %s. Public figures for applications like these: %s. Blended: %s." % (
        b["hits"], what, pct(b["rate"]), pct(b["public"]), pct(b["blended"]))


def ranking_line(kind, r):
    what = "an interview" if kind == "interview" else "an offer"
    if not r:
        return "Ranking check: shows after %d results, with at least one that led to %s and one that didn't." % (
            MIN_RANK, what)
    return ("Ranking check, over %d results: when one application led to %s and another didn't, LVLme had rated the one "
            "that did higher %s of the time (half would be a coin toss)." % (r["results"], what, pct(r["share"])))


def lines(s):
    """Plain text for the agent summary and the weekly note."""
    out = []
    for kind in KINDS:
        out.append("- Chance of %s, by the band LVLme gave on the day:" % ("an interview" if kind == "interview" else "an offer"))
        out += ["  - " + band_line(kind, b) for b in s[kind]["bands"]] + ["  - " + ranking_line(kind, s[kind]["ranking"])]
    if s["unmatched"]:
        out.append("- %d sent application%s had no LVLme odds on the day (no role id, or the role was not scored), so "
                   "%s left out." % (s["unmatched"], "" if s["unmatched"] == 1 else "s",
                                     "it is" if s["unmatched"] == 1 else "they are"))
    out.append("- Public figures: %s (%s, %s)." % (SOURCE["name"], SOURCE["date"], SOURCE["url"]))
    return out


def summary_lines(s):
    if not s:
        return []
    return ["", "## How right has LVLme been (advisory: changes no score)"] + lines(s)


def static_html(s):
    if not s:
        return ""
    items = "".join("<li>%s</li>" % html.escape(t.strip()[2:]) for t in lines(s))
    return '<h3>How right has LVLme been?</h3><p class="small sub">%s</p><ul class="small">%s</ul>' % (
        html.escape(NOTE), items)
