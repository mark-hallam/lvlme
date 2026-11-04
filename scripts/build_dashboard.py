#!/usr/bin/env python3
"""Build the dashboard and the agent briefing from the scored runs.

Writes
  report/index.html                 the dashboard, one self-contained page
  report/for-agents/SUMMARY.md      plain-text briefing for the person's other AI agents
  report/for-agents/dashboard.json  every number on the dashboard, machine-readable
  campaign/metrics-history.json     north-star metric values per run date

The page leads with the journey: the measured Day 1, every scored day since,
and where the plan is expected to take the person (with a best case and a "do
nothing" line). A what-if rail switches plan actions on and off, and every
number on the page updates. Views: Level up (the next level, the quests that
get there, level history and the progress streak; see docs/LEVELS.md),
Organisations, Path to the top band (only
if eval/ceilings.json exists), What moves you, Roles, SWOT and TOWS (only if
eval/swot.json exists), Plan, Evidence, Market. A right-hand pane drills into
any organisation, role, factor, action or piece of evidence; its home state is
Start here: Do next, Warm paths and Biggest unlocks.

Warm paths (campaign/warm-paths.json, see _warm_paths.py) show how far each
contact at each organisation has come, followed to would refer: a small strip
per organisation, the contacts in its pane, and a section in both agent files.
Progress only: nothing here reads it into a score.

One yardstick for actions: Do next, the quests, the badges, the plan list and
the action pane all use one ranked list (the actions on the path to the next
level first, in target date order, then the most points per hour), and every
action shows one points number there, its expected points toward the next level
counting its chance. Only the What if rail shows another number, what an action
adds "with everything else on", labelled that way.

The page makes no external requests, is light by default with a readable dark
switch, works on a phone, and its motion is optional: everything is drawn in
its final state first, and reduced motion is respected. The key numbers (best
match, level, outlook, Do next, best role per organisation), the level card and
the Level up view are also rendered into the HTML here, so they read the same
without JavaScript; the page script hides the static summary once it has drawn
the live page. Internal ids stay off the main surfaces (they stay in the action
pane): action titles drop a bracketed id and name another action by its short
title (people_title).

Plan actions with status later are parked: off the active cap, and out of the
projection, the next-level sets and the quests unless switched on in the
what-if rail (they start switched off).

Projection (mirrored by project() in the page script): actions in target-date
order; each effect raises a factor by `delta` or to `set_at_least`, only for
roles in its scope; a factor never rises more than projection_caps over today
or above 5; the expected path weights each rise by the action's chance, the
best case assumes every action lands; done and dropped actions are already in
(or out of) today's scores. A role whose eligibility blocker cannot be cleared
(judgement hard_eligibility_block, or a blocker type in
plan.eligibility_blockers.hard_types) keeps eligibility at 0.

Sensitive mode (config privacy.sensitive_mode, on by default) applies to the
two agent files: evidence text, contact names, compensation and claims-audit
text are left out; privacy.redact_terms, contact names and money amounts are
replaced in any remaining text. Contact names are hidden on the page too,
unless privacy.show_contact_names_in_dashboard is true.

Usage
  python3 scripts/build_dashboard.py --workspace PATH
"""
import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _public_link as PL  # noqa: E402
import _dashboard_assets as A  # noqa: E402
import _levels as L  # noqa: E402
import _levels_html as LH  # noqa: E402
import _posting_checks as PC  # noqa: E402
import _applications as AP  # noqa: E402
import _calibration as CAL  # noqa: E402
import _research as RS  # noqa: E402
import _stories as STY  # noqa: E402
import _practice as PR  # noqa: E402
import _public as PB  # noqa: E402
import _doors as DR  # noqa: E402
import _autopilot as APL  # noqa: E402
import _static_html as ST  # noqa: E402
import _warm_paths as W  # noqa: E402

DIMS = C.DIMENSIONS
DIM_HELP = {
    "D1": "How well your experience meets the hard requirements in the posting: years in a similar role, domain, named skills, degree.",
    "D2": "Shipped work a reviewer can check, relevant to this role and this organisation's products.",
    "D3": "People inside the organisation who know your work and would vouch or refer. The single biggest lever.",
    "D4": "Something this organisation values that most applicants lack.",
    "D5": "What a hiring manager finds when they look you up: writing, code, posts, talks.",
    "D6": "Work rights, visa route and location fit for where the role sits. A blocker you can't clear scores zero.",
    "D7": "A résumé, portfolio and story tailored to this exact role.",
}
STATUS_ORDER = {"doing": 0, "todo": 1, "later": 2, "done": 3, "dropped": 4}
STATUS_NAMES = {"doing": "in progress", "todo": "to do", "later": "parked for later", "done": "done", "dropped": "dropped"}
OWNERS = {"you": "You", "agent": "Your agent", "both": "You and your agent"}
DEFAULT_CAPS = {"D1": 0, "D2": 1, "D3": 2, "D4": 1, "D5": 1, "D6": 1, "D7": 3}
DEFAULT_HARD_TYPES = ["us_person_export_control", "citizenship", "security_clearance"]
CLAIM_STATUSES = [("supported", "Supported"), ("overstated", "Overstated"), ("unsupported", "Unsupported"),
                  ("contradicted", "Contradicted"), ("pending", "Waiting to be checked")]
TOWS = {"SO": "Use a strength to seize an opportunity", "ST": "Use a strength to blunt a threat",
        "WO": "Fix a weakness to unlock an opportunity", "WT": "Avoid the trap where a weakness meets a threat"}
ID_RX = r"[A-Z]{1,3}[0-9]{2,}"  # action, evidence and question ids (schemas/plan, evidence)
MAX_SLOTS = 8            # categorical colours; with more organisations the rest share "Other"
OTHER_KEY = "+other"     # cannot clash with a target id (ids are [a-z0-9_])
SAMPLE_UNTIL_RUNS = 7    # the made-up sample progress toggle shows only below this many runs, and only with ?preview=1
MONTHS = {"January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"}

# --------------------------------------------------------------- text


def clean(s):
    """Visible copy: no markdown bold, no dashes as punctuation, factor names instead of codes."""
    if s is None:
        return ""
    s = str(s).replace("**", "")
    s = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", s)
    s = re.sub(r"\s*[–—]\s*", ", ", s)
    s = re.sub(r"\s+-\s+", ", ", s)
    return re.sub(r"\bD([1-7])\b(\s+(\w+))?", _factor_name, s).strip()


def _factor_name(m):
    """'D4' becomes 'Org-specific edge'; 'D4 edge' too, rather than 'Org-specific edge edge'."""
    name, rest = C.DIMENSION_NAMES["D" + m.group(1)], m.group(2) or ""
    if m.group(3) and m.group(3).lower() == name.split()[-1].lower():
        return name
    return name + rest


def people_title(title, short, known):
    """An action title for people: a bracketed internal id such as "(Q01)" is dropped, and another
    action's id ("once A04 is done") becomes that action's short title in quotes. short maps action
    ids to short titles; known is every id in the workspace (actions, evidence, questions)."""
    t = re.sub(r"\s*\((?:%s)(?:\s*,\s*(?:%s))*\)" % (ID_RX, ID_RX), lambda m: _drop_ids(m, known), clean(title))
    return re.sub(r"\b(%s)\b" % ID_RX, lambda m: "\u201c%s\u201d" % short[m.group(1)] if m.group(1) in short else m.group(1), t)


def _drop_ids(m, known):
    ids = re.findall(ID_RX, m.group(0))
    return "" if all(i in known for i in ids) else m.group(0)


def short_title(title):
    """The first clause of a title (up to a colon), at most six words."""
    words = clean(title).split(":")[0].split()
    return " ".join(words[:6]) + ("\u2026" if len(words) > 6 else "")


def web_url(u):
    return u if isinstance(u, str) and re.match(r"^https?://", u) else ""


def hours(h):
    try:
        h = float(h)
    except (TypeError, ValueError):
        return ""
    if h < 1:
        return "%d minutes" % round(h * 60)
    return "%s hour%s" % (("%g" % h), "" if h == 1 else "s")


def add_days(iso, days):
    return (dt.date.fromisoformat(iso) + dt.timedelta(days=days)).isoformat()


def short_date(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, d.strftime("%b"), d.year)

# --------------------------------------------------------------- loading


def open_disputes(ws):
    """{(role id, D1 D2 or D4): (scorer's score, reviewer's score)} for disagreements still waiting for a tie-break."""
    out = {}
    for path in sorted(glob.glob(C.wpath(ws, "eval", "reviews", "*.json"))):
        for d in (C.load_json(path, {}) or {}).get("disputes") or []:
            m = re.match(r"^(.+)/(D[124])$", d.get("item_id", ""))
            if m and d.get("decided_by") == "awaiting_tie_break":
                out[(m.group(1), m.group(2))] = ((d.get("scorer") or {}).get("score"), (d.get("reviewer") or {}).get("score"))
    return out


class Data:
    """Everything the page and the agent files are built from."""

    def __init__(self, ws, config, today=None):
        self.ws, self.config = ws, config
        files = sorted(f for f in glob.glob(C.wpath(ws, "eval", "runs", "*.json"))
                       if re.match(r"\d{4}-\d{2}-\d{2}\.json$", os.path.basename(f)))
        runs = [(os.path.basename(f), C.load_json(f)) for f in files]
        for name, run in runs:
            if not (run.get("counts") or {}).get("judged", 1):  # saved before score.py refused these
                print("lvlme: ignoring eval/runs/%s: nothing was judged, so it is not a measurement "
                      "(it can be deleted)." % name, file=sys.stderr)
        runs = [(name, run) for name, run in runs if (run.get("counts") or {}).get("judged", 1)]
        if not runs:
            raise SystemExit("lvlme: no scored runs in eval/runs/ yet. Ask your agent to run LVLme.")
        self.run_files = [name for name, _ in runs]
        self.runs = [run for _, run in runs]
        self.cur = self.runs[-1]
        self.prev = self.runs[-2] if len(self.runs) > 1 else None
        load = lambda *p: C.load_json(C.wpath(ws, *p), None)  # noqa: E731
        self.plan = load("campaign", "plan.json") or {}
        self.evidence = load("profile", "evidence.json") or {}
        self.network = load("profile", "network.json")
        self.warm = load("campaign", "warm-paths.json")   # progress only: never scored
        self.apps = load("campaign", "applications.json")  # progress only: never scored
        self.doors = load("market", "doors.json")            # progress only: never scored
        self.week = APL.newest_note(ws)                      # Autopilot's latest This week note, if any
        self.today = today or C.today_in(config)            # follow-ups fall due, and doors pass, by the calendar
        self.calib = CAL.summary(ws, self.apps, self.today) if self.apps else None   # advisory: never scored
        self.orgs_doc = load("market", "orgs.json")
        self.stories = load("profile", "stories.json")       # progress only: never scored
        bank = load("campaign", "questions.json")
        self.asked = PR.summary(bank) if bank else None      # interview practice and debriefs
        self.public = PB.page_data(load("campaign", "public.json"), config, self.plan, self.evidence, self.doors,
                                   self.today)               # build in public: drafts only, never scored
        self.packs = {}                                      # research packs, written by main() before the page
        self.claims = (load("profile", "claims-audit.json") or {}).get("claims", [])
        self.swot = load("eval", "swot.json")
        self.ceilings = load("eval", "ceilings.json")
        judgements = load("eval", "judgements.json") or {}
        self.judgements = judgements.get("roles", {})
        self.judged_by = judgements.get("judged_by")         # which AI agent judged: another can judge differently
        self.open_disputes = open_disputes(ws)               # blind reviewer disagreed, no tie-break yet
        self.profile = load("eval", "profile-dimensions.json") or {}
        self.roles_doc = load("market", "roles", "latest.json") or {}
        self.suspicious = PC.suspicious_ids(self.roles_doc)
        self.role_index = {r["id"]: r for r in self.roles_doc.get("roles", [])}
        self.targets = C.target_ids(config)
        self.org_names = C.target_names(config)
        self.fam_names = C.family_names(config)
        self.weights = C.weights_of(config)
        self.actions = sorted(self.plan.get("actions", []),
                              key=lambda a: (STATUS_ORDER.get(a.get("status"), 9), -priority(a), a.get("id", "")))
        self.active = sorted([a for a in self.actions if a.get("status") in C.ACTIVE_STATUSES],
                             key=lambda a: (-priority(a), STATUS_ORDER.get(a.get("status"), 9), a.get("id", "")))
        self.parked = sorted([a for a in self.actions if a.get("status") == "later"],
                             key=lambda a: (-priority(a), a.get("id", "")))
        self.privacy = config.get("privacy") or {}
        self.metrics_history = []

    def org(self, oid):
        return self.org_names.get(oid, oid)


def priority(a):
    """Expected points x roles affected x chance / effort hours."""
    try:
        return round(float(a.get("expected_points", 0)) * float(a.get("roles_affected", 0))
                     * float(a.get("chance", 0)) / float(a.get("effort_hours") or 1), 2)
    except (TypeError, ValueError):
        return 0.0


def top_roles(run, n=5):
    """The n best judged roles (a role not judged yet has no real fit score)."""
    return sorted((r for r in run["roles"] if r.get("judged", True)), key=lambda r: (-r["fit"], r["role_id"]))[:n]


def top5_avg(run):
    roles = top_roles(run)
    return round(sum(r["fit"] for r in roles) / len(roles), 1) if roles else 0.0


def update_metrics_history(data):
    path = C.wpath(data.ws, "campaign", "metrics-history.json")
    hist = [m for m in (C.load_json(path, []) or []) if m.get("date") != data.cur["run_date"]]
    hist.append({"date": data.cur["run_date"], "top5_avg": top5_avg(data.cur),
                 "metrics": {m["id"]: m["current"] for m in data.plan.get("north_star", [])}})
    hist.sort(key=lambda m: m["date"])
    C.write_json(path, hist)
    data.metrics_history = hist


def dimension_moved(first, last, dim, orgs):
    """True if any in-scope role open in both runs changed its score on dim (None if none in common)."""
    def scores(run):
        return {r["role_id"]: r["scores"][dim]["score"] for r in run["roles"]
                if orgs in (None, "all") or r["org"] in orgs}
    a, b = scores(first), scores(last)
    common = set(a) & set(b)
    if not common:
        return None
    return any(a[i] != b[i] for i in common)


def stale_actions(data):
    """Doing actions with 3 or more runs since started_on and no movement: no in-scope role changed its
    score on the action's dimension, and its linked north-star metric (if any) did not change."""
    out = {}
    for a in data.actions:
        if a.get("status") != "doing" or not a.get("started_on") or a.get("dimension") not in DIMS:
            continue
        runs = [r for r in data.runs if r["run_date"] >= a["started_on"]]
        if len(runs) < 3:
            continue
        moved = dimension_moved(runs[0], runs[-1], a["dimension"], a.get("orgs", "all"))
        if moved is None:
            continue
        if a.get("metric"):
            vals = [m["metrics"].get(a["metric"]) for m in data.metrics_history if m["date"] >= a["started_on"]]
            vals = [v for v in vals if v is not None]
            moved = moved or (len(vals) > 1 and vals[0] != vals[-1])
        if not moved:
            out[a["id"]] = len(runs)
    return out


def git_first_commit(ws, rel):
    """Short hash of the commit that first added rel, if the workspace is its own git repository."""
    if not os.path.exists(os.path.join(ws, ".git")):
        return None
    try:
        out = subprocess.run(["git", "-C", ws, "log", "--diff-filter=A", "--format=%h", "--", rel],
                             capture_output=True, text=True, timeout=10).stdout.split()
        return out[-1] if out else None
    except (OSError, subprocess.SubprocessError):
        return None

# ------------------------------------------------------------ projection


def org_groups(targets, names):
    """Colour slots follow config order. Up to 8 organisations get their own slot; with more,
    the first 7 keep theirs and the rest share a neutral "Other"."""
    own = targets if len(targets) <= MAX_SLOTS else targets[:MAX_SLOTS - 1]
    groups, group_of = {}, {}
    for i, t in enumerate(own):
        groups[t] = {"name": names.get(t, t), "c": A.PALETTE[i][0], "cd": A.PALETTE[i][1], "members": [t]}
        group_of[t] = t
    rest = [t for t in targets if t not in group_of]
    if rest:
        groups[OTHER_KEY] = {"name": "Other", "c": A.OTHER[0], "cd": A.OTHER[1], "members": rest}
        group_of.update({t: OTHER_KEY for t in rest})
    return groups, group_of


def action_effects(a, weights):
    """The action's effects (an empty list means no score change), or, when the plan lists none,
    one estimated from expected_points on its dimension and orgs."""
    if "effects" in a:
        return [dict(e, scope=e.get("scope") or {}) for e in a["effects"] or []], False
    dim, w, total = a.get("dimension"), weights.get(a.get("dimension"), 0), sum(weights.values()) or 100
    if dim not in DIMS or not w or not a.get("expected_points"):
        return [], False
    delta = round(float(a["expected_points"]) * 5.0 * total / (100.0 * w), 2)
    orgs = a.get("orgs")
    return [{"dimension": dim, "delta": delta, "scope": {"orgs": orgs} if isinstance(orgs, list) else {}}], True


# The projection maths lives in _levels.py, shared with the level-up view.
in_scope, r1, fit_of, project = L.in_scope, L.r1, L.fit_of, L.project

# ------------------------------------------------------------ page data


def posting_label(p):
    """The role's posting check for the page: nothing for a likely real opening, a quiet note otherwise."""
    pc = p.get("posting_check") or {}
    return {"pc": clean(pc.get("note")), "pcl": pc.get("label")} if pc.get("label") in ("check_first", "suspicious") else {}


def build_roles(data, group_of, hard_types):
    cleared = set((data.config.get("candidate") or {}).get("eligibility_cleared") or [])
    roles = []
    for r in data.cur["roles"]:
        rid, j, p = r["role_id"], data.judgements.get(r["role_id"]) or {}, data.role_index.get(r["role_id"]) or {}
        types = sorted({b.get("type") for b in p.get("eligibility_blockers") or []} - cleared - {None})
        blocked = bool(r.get("eligibility_blocked"))
        hard = bool(j.get("hard_eligibility_block")) or (blocked and any(t in hard_types for t in types))
        roles.append({
            "id": rid, "org": r["org"], "g": group_of.get(r["org"], OTHER_KEY), "on": data.org(r["org"]),
            "title": clean(r["title"]), "family": r.get("family", ""),
            "loc": [clean(x) for x in r.get("locations") or []][:3], "url": web_url(r.get("url")),
            "lc": r.get("location_class") or "other", "blocked": blocked, "hard": hard,
            "bt": ", ".join(C.BLOCKER_NAMES.get(t, t) for t in types),
            "hrl": bool(r.get("hard_requirement_lacking")), "judged": r.get("judged", True),
            "awaiting": r.get("awaiting_review") or [],
            "disp": {d: list(v) for (i, d), v in data.open_disputes.items() if i == rid},
            "s": [r["scores"][d]["score"] for d in DIMS], "n": [clean(r["scores"][d].get("note")) for d in DIMS],
            "e": [r["scores"][d].get("evidence") or [] for d in DIMS],
            "fit": r["fit"], "ib": r["interview_band"], "ob": r["offer_band"],
            "adj": [clean(x) for x in r.get("adjustments") or []], "rn": clean(r.get("reviewer_note")),
            "hardReq": [clean(h) for h in (p.get("hard_requirements") or [])[:5]],
            **posting_label(p),
        })
    roles.sort(key=lambda x: (not x["judged"], -x["fit"], x["id"]))   # an unjudged role is never the best role
    return roles


def build_actions(data, end):
    acts = data.plan.get("actions", [])
    slots = int(data.plan.get("max_active", 8))
    now_ids = {a["id"] for a in data.active[:slots]}
    stale = stale_actions(data)
    metric_names = {m["id"]: m["name"] for m in data.plan.get("north_star", [])}

    def when(a):
        if a.get("target_date"):
            return a["target_date"]
        if a.get("status") in ("done", "dropped"):
            return a.get("finished_on") or data.cur["run_date"]
        return end
    short = {a["id"]: short_title(a["title"]) for a in acts}
    known = set(short) | {e.get("id") for e in data.evidence.get("items", [])} | {
        q.get("id") for q in data.evidence.get("open_questions") or []}
    out = []
    for a in sorted(acts, key=lambda a: (when(a), a["id"])):
        effects, derived = action_effects(a, data.weights)
        st = a.get("status", "todo")
        out.append({
            "id": a["id"], "title": people_title(a["title"], short, known), "why": clean(a.get("why")),
            "owner": OWNERS.get(a.get("owner", "you"), "You"), "effort": hours(a.get("effort_hours")),
            "hours": _num(a.get("effort_hours")),
            "status": st, "date": when(a), "dated": bool(a.get("target_date")), "p": float(a.get("chance", 0)),
            "late": bool(st in ("todo", "doing") and a.get("target_date") and a["target_date"] < data.today),
            "effects": effects, "derived": derived, "done_when": clean(a.get("done_when")),
            "dim": a.get("dimension"), "priority": priority(a), "stale": stale.get(a["id"]),
            **({"susp": True, "why": clean(((a.get("why") or "") + " Every role it names looks stale or reposted, "
                                            "so it ranks lower: check those postings first.").strip())}
               if PC.only_suspicious(a, data.suspicious) else {}),
            "group": "now" if a["id"] in now_ids else st if st in ("done", "dropped") else "later",
            "metric": clean(metric_names.get(a.get("metric"), "")), "draft": a.get("draft", ""),
            "doneEvidence": clean(a.get("done_evidence")), "notes": clean(a.get("notes")),
        })
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def end_date(data, run_date):
    if data.plan.get("end_date"):
        return max(data.plan["end_date"], add_days(run_date, 14))
    dated = [a["target_date"] for a in data.plan.get("actions", [])
             if a.get("target_date") and a.get("status") in ("todo", "doing")]
    return max([add_days(run_date, 90)] + [add_days(d, 14) for d in dated])


def build_orgs(data, roles, groups):
    d3 = data.profile.get("D3") or {}
    net = (data.network or {}).get("orgs") or {}
    paths = (data.network or {}).get("second_degree") or []
    out = {}
    for g, info in groups.items():
        lr = [x for x in roles if x["g"] == g]
        if not lr:
            continue
        single = info["members"][0] if len(info["members"]) == 1 else None
        best = ((data.cur.get("per_org") or {}).get(single) or {}).get("role_id") if single else None
        out[g] = dict(info, count=len(lr), blocked=sum(1 for x in lr if x["blocked"]),
                      judged=sum(1 for x in lr if x["judged"]),
                      best=best if best in {x["id"] for x in lr} else lr[0]["id"],
                      network=clean((d3.get(single) or {}).get("note")) if single else "",
                      first=(net.get(single) or {}).get("count") if single else None,
                      paths=[{"status": clean(p.get("status")).replace("_", " "), "note": clean(p.get("note"))}
                             for p in paths if single and p.get("org") == single])
    return out


def home_class(config):
    classes = (config.get("locations") or {}).get("classes") or []
    home = ((config.get("candidate") or {}).get("home_region") or "")
    for c in classes:
        if C.matches_any(c.get("keywords"), home):
            return c["id"]
    return classes[0]["id"] if classes else "other"


def build_market(data, roles, groups, group_of, locations, home):
    summ = data.roles_doc.get("summary") or {}
    fetched = summ.get("total_postings_fetched") or {}
    matched = summ.get("matched_counts") or {}
    return {
        "fetched": sum(fetched.values()) if fetched else None, "total": len(roles),
        "home": home, "homeCount": sum(1 for x in roles if x["lc"] == home),
        "new": len(summ.get("new_role_ids") or []), "closed": len(summ.get("closed_role_ids") or []),
        "blocked": sum(1 for x in roles if x["blocked"]),
        "byLocation": {k: sum(1 for x in roles if x["lc"] == k) for k in locations},
        # from the job-board summary when there is one; else counted from the roles themselves (a campaign made
        # from a LVLme quick result has roles but no board summary yet)
        "byOrgFamily": {o: {f: (matched[o].get(f, 0) if o in matched else
                                sum(1 for x in roles if x.get("org") == o and x.get("family") == f))
                            for f in data.fam_names} for o in data.targets},
        "fetchedOn": data.roles_doc.get("fetched_on") or "",
    }


def build_runs(data, group_of):
    out = []
    for f, rr in zip(data.run_files, data.runs):
        roles = [x for x in rr.get("roles") or [] if x.get("judged", True)]   # an unjudged role is not a measurement
        top = max(roles, key=lambda x: x["fit"]) if roles else {"fit": 0, "interview_band": "Almost none", "title": ""}
        by_group = {}
        for x in roles:
            g = group_of.get(x["org"], OTHER_KEY)
            by_group[g] = max(by_group.get(g, 0), x["fit"])
        out.append({"date": rr["run_date"], "rubric_version": rr.get("rubric_version"), "top": top["fit"], "ib": top["interview_band"], "role": clean(top["title"]),
                    "orgs": by_group, "commit": git_first_commit(data.ws, os.path.join("eval", "runs", f))})
    return out


def build_evidence(data):
    items = []
    for e in data.evidence.get("items", []):
        items.append({"id": e["id"], "claim": clean(e.get("claim")), "cat": e.get("kind", "other"),
                      "status": PL.effective_level(e), "dims": e.get("dimensions") or [],
                      "notes": clean(e.get("notes")),
                      "sources": [{"type": (s.get("type") or "").replace("_", " "), "ref": s.get("ref", ""),
                                   "url": web_url(s.get("ref")), "note": clean(s.get("note")),
                                   "checked": s.get("checked_on", "")} for s in e.get("sources") or []]})
    return items


def build_swot(data, actions):
    sw = data.swot
    if not sw:
        return None
    names = {"S": "strengths", "W": "weaknesses", "O": "opportunities", "T": "threats"}

    def grid(scope, name, g):
        return {"scope": scope, "name": name, **{k: [{"id": i.get("id"), "t": clean(i.get("text")),
                                                     "ev": i.get("evidence") or [], "src": clean(i.get("source"))}
                                                    for i in g.get(q) or []] for k, q in names.items()}}
    grids = [grid("overall", "Overall", sw.get("overall") or {})]
    for org, g in sorted((sw.get("per_org") or {}).items(), key=lambda kv: data.targets.index(kv[0])
                         if kv[0] in data.targets else 99):
        grids.append(grid(org, data.org(org), g))
    known = {a["id"] for a in actions}
    tows = [{"id": s.get("id"), "k": s.get("type", ""), "name": TOWS.get(s.get("type", ""), ""), "t": clean(s.get("text")),
             "uses": s.get("uses") or [], "a": [x for x in s.get("actions") or [] if x in known],
             "scope": "Overall" if s.get("scope") in (None, "overall") else data.org(s["scope"])}
            for s in sw.get("strategies") or []]
    return {"grids": grids, "tows": tows}


def build_ceilings(data, roles_by_id, group_of):
    """The "Path to the top band" view, from eval/ceilings.json (see schemas/ceilings.schema.json)."""
    x = data.ceilings
    if not x:
        return None
    target = int(x.get("target_fit", 85))
    reach = []
    for r in x.get("roles") or []:
        cur = roles_by_id.get(r.get("role_id"))
        reach.append({"id": r.get("role_id"), "g": group_of.get(r.get("org"), OTHER_KEY), "on": data.org(r.get("org")),
                      "title": clean(r.get("title")), "loc": clean(", ".join((r.get("locations") or [])[:2])),
                      "now": cur["fit"] if cur else r.get("now", 0), "likely": r.get("likely_12_months", 0),
                      "ceil": r.get("ceiling", 0), "ceilHist": max(r.get("ceiling_if_confirmed", 0), r.get("ceiling", 0)),
                      "open": bool(cur), "binding": C.DIMENSION_NAMES.get(r.get("binding_constraint"), "")})
    reach.sort(key=lambda r: (-r["ceilHist"], -r["likely"], -r["now"]))
    odds, wl = x.get("odds") or {}, x.get("watchlist") or {}
    return {
        "target": target, "generated": x.get("generated") or data.cur["run_date"], "how": clean(x.get("how")),
        "counts": [[c.get("value"), clean(c.get("label"))] for c in x.get("counts") or []], "reach": reach,
        "factors": [{"dim": f["dimension"], "now": clean(f.get("now")), "five": clean(f.get("five_looks_like")),
                     "gap": clean(f.get("gap")), "moves": [clean(m) for m in f.get("moves") or []],
                     "effort": clean(f.get("effort")), "chance": clean(f.get("chance"))}
                    for f in x.get("factors") or [] if f.get("dimension") in DIMS],
        "phases": [{"phase": clean(p.get("phase")), "window": clean(p.get("window")),
                    "steps": [clean(s) for s in p.get("steps") or []]} for p in x.get("phases") or []],
        "roadmap": [{"label": clean(r.get("label")),
                     "phases": [{"phase": clean(ph.get("phase")), "likely": ph.get("fit_likely", 0),
                                 "full": ph.get("fit_if_every_step_lands", 0), "band": ph.get("band_if_every_step_lands", "")}
                                for ph in r.get("phases") or []]} for r in x.get("roadmap") or []],
        "odds": {"statement": clean(odds.get("statement")), "top": clean(odds.get("reach_target_within_12_months")),
                 "good": clean(odds.get("reach_good")), "goodBy": odds.get("reach_good_by") or "",
                 "why": [clean(w) for w in odds.get("why_not_higher") or []]},
        "create": [{"t": clean(c.get("strategy")), "how": clean(c.get("how")), "lifts": clean(c.get("lifts"))}
                   for c in x.get("create_the_role") or []],
        "watch": {"titles": [clean(t) for t in wl.get("title_patterns") or []],
                  "places": [clean(t) for t in wl.get("locations_priority") or []],
                  "good": [clean(t) for t in wl.get("requirement_patterns_good") or []],
                  "exclude": [clean(t) for t in wl.get("exclude") or []], "rule": clean(wl.get("alert_rule"))},
    }


def build_data(data):
    cfg, run, plan = data.config, data.cur, data.plan
    run_date = run["run_date"]
    groups, group_of = org_groups(data.targets, data.org_names)
    for r in run["roles"]:
        group_of.setdefault(r["org"], OTHER_KEY)
    hard_types = (plan.get("eligibility_blockers") or {}).get("hard_types", DEFAULT_HARD_TYPES)
    roles = build_roles(data, group_of, hard_types)
    if any(x["g"] == OTHER_KEY for x in roles) and OTHER_KEY not in groups:
        groups[OTHER_KEY] = {"name": "Other", "c": A.OTHER[0], "cd": A.OTHER[1], "members": []}
    end = end_date(data, run_date)
    actions = build_actions(data, end)
    baseline = min(plan.get("baseline_date") or data.runs[0]["run_date"], data.runs[0]["run_date"])
    caps = dict(DEFAULT_CAPS, **(plan.get("projection_caps") or {}))
    locations = {c["id"]: c.get("name", c["id"]) for c in (cfg.get("locations") or {}).get("classes") or []}
    default_class = (cfg.get("locations") or {}).get("default_class") or "other"
    locations.setdefault(default_class, "Other")
    home = home_class(cfg)
    first = (data.metrics_history or [{}])[0].get("metrics", {})
    goal, report, cand = cfg.get("goal") or {}, cfg.get("report") or {}, cfg.get("candidate") or {}
    runs = build_runs(data, group_of)
    days, streak = L.progress_days(data.runs, data.evidence.get("items", []), plan.get("actions", []))
    out = {
        "meta": {
            "run_date": run_date, "baseline": baseline, "end": end, "title": clean(report.get("title")) or "Career campaign",
            "subtitle": clean(report.get("subtitle")), "fictional": bool(cfg.get("fictional")),
            "person": clean(cand.get("display_name")), "horizon": goal.get("horizon_months", 12),
            "principle": clean(plan.get("principle")),
            "outlook": {"band": run["outlook"]["band"], "text": clean(run["outlook"]["text"]),
                        "reasons": [clean(x) for x in run["outlook"].get("reasons") or []]},
            "sample_allowed": len(data.runs) < SAMPLE_UNTIL_RUNS, "git": os.path.exists(os.path.join(data.ws, ".git")),
            "built": short_date(run_date), "judged": C.judged_by_line(data.judged_by),
            "rubric_comparison_note": ("The scoring rules changed from version %s to %s, so this change is not comparable." %
                                        (data.prev.get("rubric_version"), data.cur.get("rubric_version"))
                                        if data.prev and data.prev.get("rubric_version") != data.cur.get("rubric_version") else ""),
        },
        "dims": DIMS, "dimNames": C.DIMENSION_NAMES, "dimHelp": DIM_HELP,
        "weights": [data.weights[d] for d in DIMS], "caps": [caps.get(d, 0) for d in DIMS],
        "families": data.fam_names, "locations": locations, "orgNames": data.org_names,
        "orgs": build_orgs(data, roles, groups), "roles": roles, "actions": actions,
        "metrics": [{"name": clean(m["name"]), "current": m["current"], "target": m["target"],
                     "start": first.get(m["id"], m["current"])} for m in plan.get("north_star", [])],
        "gaps": [{"title": clean(g["title"]), "why": clean(g.get("why")), "dim": g.get("dimension"),
                  "points": g["points_gain"], "roles": g["roles_affected"], "kind": g.get("kind") or "build_it"}
                 for g in run.get("gaps", [])],
        "vtu": [{"q": clean(v["question"]), "why": clean(v["why"])} for v in run.get("verify_to_unlock", [])],
        "evidence": build_evidence(data),
        "claims": [{"id": c["id"], "text": clean(c.get("text")), "status": c.get("status", "pending"),
                    "better": clean(c.get("suggested_wording")), "url": web_url(c.get("source")),
                    "ev": c.get("evidence") or []} for c in data.claims],
        "market": build_market(data, roles, groups, group_of, locations, home),
        "runs": runs, "swot": build_swot(data, actions), "progress": days, "streak": streak,
        "experiments": [{"date": x.get("date"), "action": clean(x.get("action") or x.get("action_id")),
                         "result": clean(x.get("result")), "decision": x.get("decision", ""), "why": clean(x.get("why"))}
                        for x in plan.get("experiments_log") or []],
        "backlog": [clean(b) for b in plan.get("backlog") or []],
        "warm": W.page_data(data.warm, data.targets, data.org_names, group_of, clean,
                            W.connection_counts(data.network)),
        "apps": AP.page_data(data.apps, data.today, data.org_names, clean),
        "doors": DR.page_data(data.doors, data.today, data.org_names),
        "calib": data.calib,
        "packs": data.packs,
        "public": data.public,
        "stories": STY.page_data(data.stories, data.config, data.evidence, data.asked),
        "week": APL.page_data(data.week, clean),
    }
    out["orgOrder"] = [g for g in groups if g in out["orgs"]]
    out["ceil"] = build_ceilings(data, {x["id"]: x for x in roles}, group_of)
    return out


def render_page(data):
    page = build_data(data)
    if not data.privacy.get("show_contact_names_in_dashboard"):
        page = _scrub_text(page, make_redactor(data, sensitive=False, hide_names=True, placeholder="a contact"))
    blob = json.dumps(page, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    card, view = LH.render(page)          # first render, readable without JavaScript; the page script redraws it
    static = ST.render(page, data.cur.get("per_org") or {})
    top = page["roles"][0] if page["roles"] else None
    out = A.TEMPLATE.replace("__TITLE__", html.escape(page["meta"]["title"])).replace(
        '<span id="builtAt"></span>', '<span id="builtAt">%s</span>' % html.escape(page["meta"]["built"]))
    out = out.replace("__BESTFIT__", str(int(top["fit"] + 0.5)) if top else "0")
    out = out.replace("__BESTROLE__", html.escape("%s: %s" % (top["on"], top["title"])) if top else "")
    out = out.replace("__LEVELCARD__", card).replace("__LEVELUP__", view).replace("__STATIC__", static)
    return out.replace("__DATA__", blob), page

# ------------------------------------------------------------ agent files


MONEY_RX = re.compile(r"(?:[$£€]\s?|\b(?:USD|AUD|EUR|GBP|CAD|NZD|SGD)\s?)\d[\d,.]*\s?[kKmM]?\b"
                      r"(?:\s*(?:to|-|–|—)\s*(?:[$£€]\s?)?\d[\d,.]*\s?[kKmM]?\b)?")


def make_redactor(data, sensitive, hide_names, placeholder="[contact]"):
    """Return a function that cleans one string.

    Contact names (full names, and first names of 3 or more letters that are
    not the person's own or a month) are hidden unless the person opted in;
    redact_terms and money amounts are hidden in sensitive mode."""
    terms = [t for t in data.privacy.get("redact_terms") or [] if t.strip()] if sensitive else []
    names = set()
    for org in ((data.network or {}).get("orgs") or {}).values():
        for c in org.get("first_degree", []):
            if c.get("name"):
                names.add(c["name"])
    for p in (data.network or {}).get("second_degree") or []:
        for k in ("via", "target_person"):
            if p.get(k) and re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][\w'-]+)+$", p[k]):
                names.add(p[k])
    names |= W.person_names(data.warm)    # a warm-path person is always a name, whatever its form
    if not hide_names:
        names = set()
    own = set(((data.config.get("candidate") or {}).get("display_name") or "").split())
    firsts = {n.split()[0] for n in names if len(n.split()) > 1}
    firsts = {f for f in firsts if len(f) >= 3 and f not in own and f not in MONTHS}
    # A one-word name ("Will", "Mark") matches with its capital only, like a first name, so the
    # words "will" and "mark" stay; and never the person's own name.
    names = {n for n in names if len(n.split()) > 1 or n.strip() not in own}
    rules = [(re.compile(r"(?<!\w)%s(?!\w)" % re.escape(t), re.I), "[redacted]") for t in sorted(terms, key=len, reverse=True)]
    rules += [(re.compile(r"(?<!\w)%s(?!\w)" % re.escape(n), re.I if len(n.split()) > 1 else 0), placeholder)
              for n in sorted(names, key=len, reverse=True)]
    rules += [(re.compile(r"(?<!\w)%s(?!\w)" % re.escape(f)), placeholder) for f in sorted(firsts, key=len, reverse=True)]

    def sub_for(word):
        def at(m):  # a placeholder that starts a sentence starts with a capital
            before = m.string[:m.start()].rstrip()
            return word[:1].upper() + word[1:] if not before or before[-1] in ".!?:" else word
        return at

    def clean_text(text):
        for rx, word in rules:
            text = rx.sub(sub_for(word), text)
        return MONEY_RX.sub("[salary]", text) if sensitive else text
    return clean_text


def scrub(value, clean_text):
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [scrub(v, clean_text) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v, clean_text) for k, v in value.items() if k != "compensation"}
    return value


def _scrub_text(value, clean_text):
    """Like scrub, but keeps every field (used when only contact names are hidden)."""
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [_scrub_text(v, clean_text) for v in value]
    if isinstance(value, dict):
        return {k: _scrub_text(v, clean_text) for k, v in value.items()}
    return value


def projection_summary(page):
    """Expected and best-case fit by the end date for the top 5 roles, with every live action on."""
    caps, weights = page["caps"], page["weights"]
    out = []
    for r in page["roles"][:5]:
        exp, _ = project(r, page["actions"], caps, weights, "exp")
        best, _ = project(r, page["actions"], caps, weights, "best")
        out.append({"role_id": r["id"], "org": r["org"], "title": r["title"], "fit_today": r["fit"],
                    "fit_expected": exp, "fit_best_case": best})
    return {"end_date": page["meta"]["end"], "baseline_date": page["meta"]["baseline"], "roles": out}


def _role_json(role, lead, fit_after, after_key="fit_after"):
    return {"role_id": role["id"], "org": role["org"], "title": role["title"], "fit_before": role["fit"],
            after_key: fit_after, "is_best_role_today": role["id"] == lead["id"]}


def _found_json(found, by_id, fit_key, lead):
    if not found:
        return None
    return {"actions": [{"id": i, "title": by_id[i].get("title", ""), "target_date": by_id[i].get("target_date")} for i in found["ids"]],
            "level_reached_on": found["date"], fit_key: found["fit"],
            "lifted_role": _role_json(found["role"], lead, found["fit"]),
            "chance_it_happens": None if found.get("chance") is None else round(found["chance"], 3),
            "exact_search": found["exact"]}


def _next_level_json(page, roles, by_id):
    """The next level for a journey: roles is every role, or one organisation's, today's best first."""
    nl = L.next_level(roles, page["actions"], page["caps"], page["weights"], page["meta"]["run_date"])
    role = roles[0]
    out = {"role_id": role["id"], "org": role["org"], "title": role["title"], "fit": role["fit"],
           "level": nl["level"], "band": nl["band"], "top_level": nl["top"]}
    if nl["top"]:
        return out, nl
    out.update(next_level=nl["next_level"], next_band=nl["next_band"], next_level_starts_at=nl["target"],
               points_to_next=nl["points_to_next"], reachable_on_expected_odds=nl["reachable"],
               whole_plan={"fit_expected": nl["plan"]["fit_expected"], "fit_best_case": nl["plan"]["fit_best"],
                           "level_reached_on": nl["plan"]["date"]})
    if nl["reachable"]:
        out["smallest_set"] = _found_json(nl["set"], by_id, "fit_expected", role)
    else:
        out["best_case_set"] = _found_json(nl.get("best_case"), by_id, "fit_if_all_work", role)
        m = nl["missing"]
        out["missing"] = {"points_short": m["points"], "ceiling_within_caps": m["ceiling"],
                          "closest_role": _role_json(m["role"], role, nl["plan"]["fit_expected"], "fit_expected"),
                          "room_by_factor": [{"dimension": x["dimension"], "name": C.DIMENSION_NAMES[x["dimension"]],
                                              "points": x["points"], "open_action_covers_it": x["covered"]} for x in m["room"]]}
    return out, nl


def levels_payload(data, page):
    """Everything the level-up view shows, for the person's other agents (every open action switched on)."""
    by_id = {a["id"]: a for a in data.plan.get("actions", [])}
    roles = {r["id"]: r for r in page["roles"]}
    if not page["roles"]:
        return None
    every = L.journey_roles(page["roles"])
    best, nl = _next_level_json(page, every, by_id)
    per_org = {}
    for g in page["orgOrder"]:
        r = roles.get(page["orgs"][g]["best"])
        if r and g != OTHER_KEY and page["orgs"][g].get("judged", 1):
            per_org[g] = _next_level_json(page, L.journey_roles(page["roles"], r, g), by_id)[0]
    lead, quests = every[0], []
    qs = L.quests(every, page["actions"], page["caps"], page["weights"], nl)
    path = set(L.path_ids(nl))
    for rank, q in enumerate(L.up_next(qs, nl), 1):
        a, raw = q["a"], by_id.get(q["a"]["id"], {})
        other = q["role"]["id"] != lead["id"]
        quests.append({"rank": rank, "id": a["id"], "title": raw.get("title", ""), "title_on_page": a["title"], "status": a["status"],
                        "owner": raw.get("owner", "you"), "effort_hours": raw.get("effort_hours"), "target_date": raw.get("target_date"),
                        "chance": a["p"], "done_when": raw.get("done_when", ""), "points_expected": q["exp"],
                        "points_if_it_works": q["works"], "points_per_hour": round(q["rate"], 2), "changes_a_score": bool(a["effects"]),
                        "lifted_role": _role_json(q["role"], lead, q["fit_after"]),
                        "on_best_role_today": {"points_expected": q["lead_exp"], "points_if_it_works": q["lead_works"]} if other else None,
                        "on_path": a["id"] in path, "on_path_to_next_level": q["crit"], "needed_for_best_case": bool(q["bc"]),
                        "tell_your_agent": L.tell_agent(dict(a, title=raw.get("title", a["title"])))})
    return {
        "how": ("Levels are the rubric's fit bands (1 Very low, 2 Low from 40, 3 Moderate from 55, 4 Good from 70, 5 Strong from 85), "
                "taken from the best fit across your roles (the page's best match), so any role can carry you to the next level. The "
                "smallest set is the fewest open actions whose expected effects (each weighted by its chance, within the projection caps) "
                "take that best fit to the next level; the date assumes they land on their target dates, and lifted_role is the role that "
                "then holds the best fit. quests is the dashboard's one ranked list of actions (Do next, the quests, the badges and the "
                "plan list all follow it): the actions on the path to the next level first (the smallest set, or when none reaches it on "
                "expected odds, the best-case set), in target date order, then the rest by points per hour. Every action shows one "
                "points number on the page, points_expected: what that action alone adds to the best fit toward the next level, chance "
                "weighted and within the caps, counted on lifted_role, with on_best_role_today when that differs. Actions that raise the "
                "same factor overlap, so quest points do not simply add up. Only the What if rail shows another number, what an action "
                "adds with everything else switched on. Nothing here is made up: it all comes from the runs and the plan."),
        "best_role": best, "per_org": per_org, "quests": quests,
        "level_history": L.level_history(page["runs"]), "streak": page["streak"], "progress_days": page["progress"],
    }


def up_next_order(actions, levels):
    """Plan actions in the page's Do next order (the rest after it, as they were)."""
    rank = {q["id"]: q["rank"] for q in (levels or {}).get("quests") or []}
    return sorted(actions, key=lambda a: rank.get(a["id"], len(rank) + 1))


def agent_payload(data, page):
    sensitive = bool(data.privacy.get("sensitive_mode", True))
    share_names = bool(data.privacy.get("share_contact_names_with_agents")) and not sensitive
    cur, goal = data.cur, data.config.get("goal") or {}
    levels = levels_payload(data, page)
    counts = {}
    for e in data.evidence.get("items", []):
        counts[e.get("level")] = counts.get(e.get("level"), 0) + 1
    payload = {
        "about": "Private career campaign data. Read only. See SUMMARY.md in this folder for the rules.",
        "generated_by": "lvlme scripts/build_dashboard.py",
        "sensitive_mode": sensitive,
        "run_date": cur["run_date"], "rubric_version": cur["rubric_version"],
        "goal": {"title": goal.get("title", ""), "description": goal.get("description", ""),
                 "horizon_months": goal.get("horizon_months", 12)},
        "outlook": cur["outlook"],
        "judged_by": data.judged_by, "judged_by_note": C.judged_by_line(data.judged_by),
        "role_counts": {"open": len(cur["roles"]), "judged": sum(1 for r in cur["roles"] if r.get("judged", True))},
        "top5_average_fit": top5_avg(cur),
        "top5_average_fit_previous": (top5_avg(data.prev) if data.prev and
                                       data.prev.get("rubric_version") == cur.get("rubric_version") else None),
        "rubric_comparison_note": ("The scoring rules changed from version %s to %s, so this change is not comparable." %
                                    (data.prev.get("rubric_version"), cur.get("rubric_version"))
                                    if data.prev and data.prev.get("rubric_version") != cur.get("rubric_version") else ""),
        "per_org": {o: (dict(b, org_name=data.org(o)) if b else None) for o, b in cur["per_org"].items()},
        "projection": projection_summary(page),
        "gaps": cur.get("gaps", []),
        "verify_to_unlock": cur.get("verify_to_unlock", []),
        "actions_active": [dict(a, priority=priority(a), late=bool(
            a.get("status", "todo") in ("todo", "doing") and a.get("target_date") and
            a["target_date"] < data.today)) for a in up_next_order(data.active, levels)],
        "actions_later": [dict(a, priority=priority(a)) for a in data.parked],
        "levels": levels,
        "actions_done": [a for a in data.actions if a.get("status") == "done"],
        "north_star": data.plan.get("north_star", []),
        "metrics_history": data.metrics_history,
        "evidence_counts": counts,
        "claims_audit_counts": {k: sum(1 for c in data.claims if c["status"] == k) for k, _ in CLAIM_STATUSES},
        "network_first_degree_counts": {o: v.get("count", 0) for o, v in ((data.network or {}).get("orgs") or {}).items()},
        "roles": [{"role_id": r["role_id"], "org": r["org"], "title": r["title"], "family": r["family"],
                   "judged": r.get("judged", True),
                   "locations": r.get("locations", []), "url": r.get("url"), "fit": r["fit"],
                   "interview_band": r["interview_band"], "offer_band": r["offer_band"],
                   "scores": {d: r["scores"][d]["score"] for d in DIMS},
                   "adjustments": r["adjustments"], "reviewer_note": r.get("reviewer_note", "")} for r in cur["roles"]],
    }
    if data.swot:
        payload["swot"] = data.swot
    if not sensitive:
        payload["evidence"] = data.evidence.get("items", [])
        payload["claims_audit"] = data.claims
        payload["roles"] = [dict(r, compensation=data.role_index.get(r["role_id"], {}).get("compensation"))
                            for r in payload["roles"]]
    if share_names and data.network:
        payload["network"] = data.network
    payload["warm_paths"] = W.agent_data(data.warm, data.targets, data.org_names, include_contacts=not sensitive)
    if data.apps is not None:
        payload["applications"] = AP.agent_data(data.apps, data.today, data.org_names)
    if data.calib:
        payload["calibration"] = data.calib
    if data.stories is not None:
        payload["stories"] = STY.page_data(data.stories, data.config, data.evidence, data.asked)
    if data.public:
        payload["build_in_public"] = data.public
    if data.packs:
        payload["research_packs"] = {o: dict(p, path="report/" + p["path"]) for o, p in data.packs.items()}
    if data.doors is not None:
        payload["doors"] = DR.page_data(data.doors, data.today, data.org_names, limit=20)
    if sensitive or not share_names:
        clean_text = make_redactor(data, sensitive, hide_names=not share_names)
        payload = scrub(payload, clean_text) if sensitive else _scrub_text(payload, clean_text)
    return payload


def _lift_md(role, before_key="fit_before", after_key="fit_after"):
    return "%s (%s) from %s to %s" % (role["title"], role["org"], _g(role[before_key]), _g(role[after_key]))


def _set_md(found):
    acts = ", ".join("%s (%s, target %s)" % (a["id"], a["title"], a["target_date"] or "none") for a in found["actions"])
    chance = "" if found["chance_it_happens"] is None else "; chance it really happens %d%%" % L.pct(found["chance_it_happens"])
    lift = found["lifted_role"]
    return "%s; level reached %s by lifting %s%s%s" % (acts, found["level_reached_on"], _lift_md(lift),
                                                       "" if lift["is_best_role_today"] else ", which would then be the best role", chance)


def _g(v):
    return "%g" % v


def _level_md(b):
    head = "%s (%s), Level %d %s, fit %s." % (b["title"], b["org"], b["level"], b["band"], _g(b["fit"]))
    if b["top_level"]:
        return [head + " Top level."]
    out = [head + " Level %d %s starts at %d: %s %s to go." % (b["next_level"], b["next_band"], b["next_level_starts_at"],
                                                              _g(b["points_to_next"]), "point" if b["points_to_next"] == 1 else "points")]
    if b["reachable_on_expected_odds"]:
        out.append("  Smallest set that gets there, counting each action's chance: " + _set_md(b["smallest_set"]) + ".")
        return out
    close = b["missing"]["closest_role"]
    out.append("  No set of open actions gets there counting their chances: the whole plan is expected to take the best fit to %s, "
               "%s short (closest role: %s)." % (_g(b["whole_plan"]["fit_expected"]), _g(b["missing"]["points_short"]),
                                                 _lift_md(close, after_key="fit_expected")))
    if b.get("best_case_set"):
        out.append("  Best case only (every action in it must work): " + _set_md(b["best_case_set"]) + ".")
    room = ", ".join("%s +%s%s" % (x["name"], _g(x["points"]), "" if x["open_action_covers_it"] else " (no open action)")
                     for x in b["missing"]["room_by_factor"])
    out.append("  Room left within the caps on the closest role: %s. Its ceiling within the caps: %s." % (
        room or "none", _g(b["missing"]["ceiling_within_caps"])))
    return out


def _quest_md(q):
    if not q["changes_a_score"]:
        pts = "protects credibility, no score change"
    elif not (q["points_expected"] or q["points_if_it_works"]):
        pts = "no points toward the next level on its own"
    else:
        pts = "+%s toward the next level expected (the page's number; +%s if it works, %s per hour)" % (
            _g(q["points_expected"]), _g(q["points_if_it_works"]), _g(q["points_per_hour"]))
        if q["on_best_role_today"]:
            pts += ", by lifting %s; on the best role today +%s expected" % (
                _lift_md(q["lifted_role"]), _g(q["on_best_role_today"]["points_expected"]))
    tag = (" [on the path to the next level]" if q["on_path_to_next_level"]
           else " [needed for the best case]" if q["needed_for_best_case"] else "")
    return "%d. %s %s%s: %s; %s, %s, target %s, owner %s. Done when: %s" % (
        q["rank"], q["id"], q["title"], tag, pts, STATUS_NAMES.get(q["status"], q["status"]), hours(q["effort_hours"]) or "effort not set",
        q["target_date"] or "none", q["owner"], q["done_when"])


def levels_md(data, lv):
    if not lv:
        return []
    lines = ["", "## Next level (fit bands of the rubric, on the best fit across roles; nothing here is made up)", "- Best role: "]
    first = _level_md(lv["best_role"])
    lines[-1] += first[0]
    lines += first[1:]
    for oid, b in lv["per_org"].items():
        rows = _level_md(b)
        lines.append("- At %s: %s" % (data.org(oid), rows[0]))
        lines += rows[1:]
    lines += ["", "## Quests (the dashboard's Do next order and points: one ranked list, one number per action)",
              "- Order: the actions on the path to the next level first, in target date order, then the most points per hour.",
              "- Points are what one action alone adds to the best fit across roles toward the next level, chance weighted and within",
              "  the caps. Actions that raise the same factor overlap, so the points do not simply add up; the smallest set above shows",
              "  what they do together."]
    lines += [_quest_md(q) for q in lv["quests"]]
    hist = ", ".join("%s Level %d %s (fit %s%s)" % (h["date"], h["level"], h["band"], _g(h["fit"]),
                                                   ", level up" if h["change"] == "up" else ", level down" if h["change"] == "down" else "")
                     for h in lv["level_history"])
    lines += ["", "## Progress",
              "- Streak: %s in a row with real progress (a fit that rose, newly checked evidence, or an action done with evidence)." % (
                  "1 scored day" if lv["streak"] == 1 else "%d scored days" % lv["streak"]),
              "- Level history, best role: %s" % hist,
              "",
              "## When the person says an action is done",
              "- They may paste what the dashboard's \"Done? Tell your agent\" button copies:",
              "  Mark action A07 done (\"title\"). Evidence: <link, file or email>.",
              "- The agent running the campaign sets status done, done_evidence and finished_on in campaign/plan.json. Done needs a",
              "  link, a file or an email reference; without one, ask for it. Any other agent appends the message to campaign/inbox.md."]
    return lines


def goal_line(goal):
    """The goal's title, then its description only when it says more (init.py starts both as the same words).

    >>> goal_line({"title": "Customer success at AI labs", "description": "Customer success at AI labs"})
    'Customer success at AI labs.'
    """
    title, desc = (goal.get("title") or "").strip().rstrip("."), (goal.get("description") or "").strip()
    same = desc.rstrip(".").lower() == title.lower()
    return "%s.%s" % (title, "" if same or not desc else " " + desc)


def summary_md(data, p):
    lines = [
        "# Career campaign: briefing for AI agents",
        "",
        "Last updated: %s. Full data: dashboard.json in this folder." % p["run_date"],
        ("Privacy: sensitive mode is ON. Employer names, third-party names and salary are left out." if p["sensitive_mode"]
         else "Privacy: sensitive mode is off. Treat everything here as private."),
        "",
        "## Rules for any agent reading this",
        "- Read only. Never apply for jobs, send emails or messages, post publicly, or change the person's accounts.",
        "- To suggest something, append a dated note to campaign/inbox.md in this workspace (one bullet per note,",
        "  say who you are, include a source for every fact). The next run checks it; facts count only once verified.",
        "- This is private. Do not copy it anywhere public.",
        "",
        "## Goal",
        goal_line(p["goal"]),
        "",
        "## Outlook",
        "- %s" % p["judged_by_note"],
        "- Chance of reaching the goal within %s months if the campaign is followed: %s" % (
            p["goal"]["horizon_months"], p["outlook"]["band"]),
        "- %s" % p["outlook"]["text"],
        "- Best match (the best fit across your open roles, a fit score, not a probability): %s of 100" % _g(
            max([r["fit"] for r in p["roles"] if r["judged"]] or [0])),
        "- Roles judged: %d of %d open. A role not judged yet has no real fit score and is left out of the best roles below." % (
            p["role_counts"]["judged"], p["role_counts"]["open"]),
        "- Average fit of the 5 best open roles: %s / 100%s" % (
            p["top5_average_fit"],
            p["rubric_comparison_note"] if p["rubric_comparison_note"] else
            "" if p["top5_average_fit_previous"] is None else " (previous run %s)" % p["top5_average_fit_previous"]),
        "",
        "## Best role at each organisation",
    ]
    for oid, b in p["per_org"].items():
        n = sum(1 for r in p["roles"] if r["org"] == oid)
        lines.append("- %s: %s" % (data.org(oid), "%s, fit %s, interview %s, offer %s" % (
            b["title"], round(b["fit"]), b["interview_band"], b["offer_band"]) if b
            else "no role judged yet (%d open, none scored)" % n if n else "no matching open role"))
    pr = p["projection"]
    lines += ["", "## Projection to %s (every open action on; expected weights each by its chance)" % pr["end_date"]]
    for r in pr["roles"]:
        lines.append("- %s: %s today, %s expected, %s if every action lands" % (
            r["title"], round(r["fit_today"]), round(r["fit_expected"]), round(r["fit_best_case"])))
    lines += ["", "## Active actions (in the dashboard's Do next order; points under Quests below)"]
    for a in p["actions_active"]:
        lines.append("- [%s] %s %s (owner: %s; done when: %s)" % (a["status"], a["id"], a["title"], a.get("owner", "you"),
                                                                 a.get("done_when", "")))
    if p.get("actions_later"):
        lines += ["", "## Parked for later (not in the projection or the next-level sets until switched on)"]
        for a in p["actions_later"]:
            lines.append("- %s %s (owner: %s; done when: %s)" % (a["id"], a["title"], a.get("owner", "you"), a.get("done_when", "")))
    lines += levels_md(data, p.get("levels"))
    lines += ["", "## Biggest gaps"]
    for g in p["gaps"]:
        lines.append("- %s: +%s fit points across %d roles. %s" % (g["title"], g["points_gain"], g["roles_affected"], g["why"]))
    lines += ["", "## Top 10 judged open roles"]
    for r in sorted((r for r in p["roles"] if r["judged"]), key=lambda r: (-r["fit"], r["role_id"]))[:10]:
        lines.append("- %s  %s: %s (interview %s, offer %s) %s" % (round(r["fit"]), data.org(r["org"]), r["title"],
                                                                  r["interview_band"], r["offer_band"], r.get("url") or ""))
    lines += ["", "## Questions only the person can answer"]
    for v in p["verify_to_unlock"]:
        lines.append("- %s (%s)" % (v["question"], v["why"]))
    lines += ["", "## Evidence and network",
              "- Evidence items by level: %s" % (", ".join("%s %d" % (k, v) for k, v in sorted(p["evidence_counts"].items())) or "none"),
              "- First-degree contacts per organisation: %s" % (", ".join(
                  "%s %d" % (data.org(o), n) for o, n in p["network_first_degree_counts"].items()) or "not mapped yet")]
    lines += W.summary_lines(p["warm_paths"], data.org)
    if p.get("applications"):
        lines += AP.summary_lines(p["applications"])
    lines += DR.summary_lines(p.get("doors"))
    lines += CAL.summary_lines(p.get("calibration"))
    lines += STY.summary_lines(p.get("stories"))
    lines += PB.summary_lines(p.get("build_in_public"))
    lines += RS.summary_lines(data.packs, data.org_names)
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the dashboard and the agent briefing.")
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--today", help="YYYY-MM-DD for follow-ups and upcoming doors (default: today in the person's time zone)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    data = Data(ws, config, C.check_date(args.today) if args.today else None)
    update_metrics_history(data)
    data.packs = RS.write_all(ws, config, data.orgs_doc, data.roles_doc, data.doors, data.today)
    page_html, page = render_page(data)
    C.write_text(C.wpath(ws, "report", "index.html"), page_html)
    payload = agent_payload(data, page)
    C.write_json(C.wpath(ws, "report", "for-agents", "dashboard.json"), payload)
    C.write_text(C.wpath(ws, "report", "for-agents", "SUMMARY.md"), summary_md(data, payload))
    print("Wrote report/index.html, report/for-agents/SUMMARY.md, report/for-agents/dashboard.json "
          "(sensitive mode %s)" % ("on" if payload["sensitive_mode"] else "off"))
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
