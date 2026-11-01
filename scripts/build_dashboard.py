#!/usr/bin/env python3
"""Build the dashboard and the agent briefing from the scored runs.

Writes
  report/index.html                 views: Overview, Trends, Roles, SWOT, Plan, Evidence
  report/for-agents/SUMMARY.md      plain-text briefing for the person's other AI agents
  report/for-agents/dashboard.json  every number on the dashboard, machine-readable
  campaign/metrics-history.json     north-star metric values per run date

The page is self-contained (inline CSS and JavaScript, no external requests),
has light and dark mode, and reads on a 320 pixel wide phone. Every chart has
hover tooltips, direct labels and a "Show as a table" view.

Sensitive mode (config privacy.sensitive_mode, on by default) applies to the
two agent files: evidence text, contact names, compensation and claims-audit
text are left out; privacy.redact_terms, contact names and money amounts are
replaced in any remaining text.

Usage
  python3 scripts/build_dashboard.py --workspace PATH
"""
import argparse
import glob
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _dashboard_assets as A  # noqa: E402

BANDS = C.BANDS
STATUS_ORDER = {"doing": 0, "todo": 1, "done": 2, "dropped": 3}
STATUS_LABEL = {"todo": "To do", "doing": "In progress", "done": "Done", "dropped": "Dropped"}
LEVELS = [("verified", "Verified"), ("corroborated", "Corroborated"), ("self_reported", "Self-reported"),
          ("unverified", "Not yet verified"), ("contradicted", "Contradicted")]
CLAIM_STATUSES = [("supported", "Supported"), ("overstated", "Overstated"), ("unsupported", "Unsupported"),
                  ("contradicted", "Contradicted"), ("pending", "Waiting to be checked")]
TOWS = [("SO", "Strength meets opportunity", "Use a strength to seize an opportunity."),
        ("ST", "Strength meets threat", "Use a strength to blunt a threat."),
        ("WO", "Weakness meets opportunity", "Fix a weakness to unlock an opportunity."),
        ("WT", "Weakness meets threat", "Avoid the trap where a weakness meets a threat.")]
ICONS = {
    "plus": '<path d="M12 7v10M7 12h10"/><circle cx="12" cy="12" r="9"/>',
    "minus": '<path d="M7 12h10"/><circle cx="12" cy="12" r="9"/>',
    "up": '<path d="M7 17 17 7M9 7h8v8"/>',
    "warn": '<path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4M12 17h.01"/>',
}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def icon(name, size=16):
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % (size, size, ICONS[name]))


def band_pill(band):
    i = BANDS.index(band) if band in BANDS else -1
    return '<span class="pill %s">%s</span>' % ("p%d" % i if i >= 0 else "pn", esc(band))


def table_view(head, rows):
    body = "".join("<tr>" + "".join(rows_cells) + "</tr>" for rows_cells in rows)
    return ("<details class='tableview'><summary>Show as a table</summary><div class='tablewrap'><table><tr>"
            + "".join("<th>%s</th>" % esc(h) for h in head) + "</tr>" + body + "</table></div></details>")

# --------------------------------------------------------------- loading


class Data:
    """Everything the page and the agent files are built from."""

    def __init__(self, ws, config):
        self.ws, self.config = ws, config
        files = sorted(f for f in glob.glob(C.wpath(ws, "eval", "runs", "*.json"))
                       if re.match(r"\d{4}-\d{2}-\d{2}\.json$", os.path.basename(f)))
        if not files:
            raise SystemExit("career-eval: no runs in eval/runs/. Run scripts/score.py first.")
        self.runs = [C.load_json(f) for f in files]
        self.cur = self.runs[-1]
        self.prev = self.runs[-2] if len(self.runs) > 1 else None
        self.plan = C.load_json(C.wpath(ws, "campaign", "plan.json"), {}) or {}
        self.evidence = C.load_json(C.wpath(ws, "profile", "evidence.json"), {}) or {}
        self.network = C.load_json(C.wpath(ws, "profile", "network.json"), None)
        self.claims = (C.load_json(C.wpath(ws, "profile", "claims-audit.json"), {}) or {}).get("claims", [])
        self.swot = C.load_json(C.wpath(ws, "eval", "swot.json"), None)
        self.orgs_intel = (C.load_json(C.wpath(ws, "market", "orgs.json"), {}) or {}).get("orgs", {})
        self.roles_doc = C.load_json(C.wpath(ws, "market", "roles", "latest.json"), {}) or {}
        self.role_index = {r["id"]: r for r in self.roles_doc.get("roles", [])}
        self.snapshots = []
        for f in sorted(glob.glob(C.wpath(ws, "market", "roles", "snapshots", "*.json"))):
            if re.match(r"\d{4}-\d{2}-\d{2}\.json$", os.path.basename(f)):
                self.snapshots.append(C.load_json(f))
        self.targets = C.target_ids(config)
        self.org_names = C.target_names(config)
        self.fam_names = C.family_names(config)
        self.colours = {t: (A.PALETTE[i] if i < len(A.PALETTE) else A.OTHER) for i, t in enumerate(self.targets)}
        self.ev_index = {e["id"]: e for e in self.evidence.get("items", [])}
        self.actions = sorted(self.plan.get("actions", []),
                              key=lambda a: (STATUS_ORDER.get(a.get("status"), 9), -priority(a), a.get("id", "")))
        self.active = sorted([a for a in self.actions if a.get("status") in ("todo", "doing")],
                             key=lambda a: (-priority(a), STATUS_ORDER.get(a.get("status"), 9), a.get("id", "")))
        self.action_index = {a["id"]: a for a in self.actions}
        self.privacy = config.get("privacy") or {}
        self.metrics_history = []

    def org(self, oid):
        return self.org_names.get(oid, oid)

    def fam(self, fid):
        return self.fam_names.get(fid, fid)


def priority(a):
    """Expected points x roles affected x chance / effort hours."""
    try:
        return round(float(a.get("expected_points", 0)) * float(a.get("roles_affected", 0))
                     * float(a.get("chance", 0)) / float(a.get("effort_hours") or 1), 2)
    except (TypeError, ValueError):
        return 0.0


def top_roles(run, n=5):
    return sorted(run["roles"], key=lambda r: (-r["fit"], r["role_id"]))[:n]


def top5_avg(run):
    roles = top_roles(run)
    return round(sum(r["fit"] for r in roles) / len(roles), 1) if roles else 0.0


def dim_avgs(run):
    roles = top_roles(run)
    return {d: (round(sum(r["scores"][d]["score"] for r in roles) / len(roles), 2) if roles else 0.0)
            for d in C.DIMENSIONS}


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
        if a.get("status") != "doing" or not a.get("started_on") or a.get("dimension") not in C.DIMENSIONS:
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

# ----------------------------------------------------------------- charts


def line_chart(cid, title, dates, series, ymax=100, unit="", compact=False, note=""):
    """A chart drawn by the page script at the container's real width, plus a table view."""
    nice = max(1, int(ymax))
    step = max(1, nice // 4) if nice > 4 else 1
    ticks = list(range(0, nice + 1, step))
    if ticks[-1] != nice:
        ticks.append(nice)
    payload = {"title": title, "dates": dates, "ymax": nice, "ticks": ticks, "unit": unit, "compact": compact,
               "series": [{"name": s["name"], "values": s["values"], "c": s["colour"][0], "cd": s["colour"][1]}
                          for s in series]}
    legend = ""
    if len(series) > 1:
        legend = '<div class="legend">' + "".join(
            '<span><i class="lkey" style="--c:%s;--cd:%s"></i>%s</span>' % (s["colour"][0], s["colour"][1], esc(s["name"]))
            for s in series) + "</div>"
    rows = [["<td class='num'>%s</td>" % esc(d)] + [
        "<td class='num'>%s</td>" % ("" if s["values"][i] is None else esc(s["values"][i])) for s in series]
        for i, d in enumerate(dates)]
    single = "" if len(dates) > 1 else "<p class='muted small'>Only one run so far. The line fills in as runs build up.</p>"
    data_json = json.dumps(payload).replace("</", "<\\/")
    return ('<div class="card chart"><div class="chart-title">%s</div>%s'
            '<div class="plot" tabindex="0" data-src="d-%s" aria-label="%s. Use the arrow keys to read values."></div>'
            '<script type="application/json" id="d-%s">%s</script>'
            '<p class="noscript-note">The chart needs JavaScript; the table below has the same numbers.</p>%s%s%s</div>'
            % (esc(title), legend, cid, esc(title), cid, data_json, single, note,
               table_view(["Date"] + [s["name"] for s in series], rows)))


def bar_chart(title, rows, max_value, unit=""):
    """rows: [{label, value, sub}]. One series, horizontal bars, direct value labels."""
    if not rows:
        return '<div class="card chart"><div class="chart-title">%s</div><p class="muted">Nothing to show yet.</p></div>' % esc(title)
    body = ""
    for r in rows:
        frac = 0.0 if not max_value else max(0.0, min(1.0, r["value"] / float(max_value)))
        tip = "%s: %s%s" % (r["label"], r["value"], unit) + (" (%s)" % r["sub"] if r.get("sub") else "")
        body += ('<div class="brow" tabindex="0" data-tip="%s"><div class="blabel">%s</div>'
                 '<div class="btrack"><div class="bfill" style="width:max(3px, calc((100%% - 64px) * %.4f))"></div>'
                 '<span class="bval">%s%s</span></div></div>' % (esc(tip), esc(r["label"]), frac, esc(r["value"]), esc(unit)))
    table = table_view(["Item", "Value", "Detail"], [
        ["<td>%s</td>" % esc(r["label"]), "<td class='num'>%s%s</td>" % (esc(r["value"]), esc(unit)),
         "<td>%s</td>" % esc(r.get("sub", ""))] for r in rows])
    return '<div class="card chart"><div class="chart-title">%s</div><div class="bars">%s</div>%s</div>' % (esc(title), body, table)

# ------------------------------------------------------------------ views


def delta(cur, prev, unit=""):
    if prev is None:
        return '<span class="muted">first run</span>'
    d = round(cur - prev, 1)
    if d == 0:
        return '<span class="muted">no change since the last run</span>'
    return '<span class="%s">%s%s%s since the last run</span>' % ("up" if d > 0 else "down", "+" if d > 0 else "", d, unit)


def ev_chips(ids, data):
    out = ""
    for eid in ids or []:
        item = data.ev_index.get(eid)
        title = "%s (%s)" % (item["claim"], item["level"].replace("_", " ")) if item else "unknown evidence id"
        out += '<span class="chip" title="%s">%s</span>' % (esc(title), esc(eid))
    return out


def status_pill(status):
    mark = "&#10003; " if status == "done" else ""
    return '<span class="st st-%s">%s%s</span>' % (esc(status), mark, esc(STATUS_LABEL.get(status, status)))


def action_row(a, data, stale, full=True):
    pr = priority(a)
    meta = ["Owner: %s" % esc(a.get("owner", "you")), "Effort: %s h" % esc(a.get("effort_hours")),
            "Feeds %s %s" % (esc(a.get("dimension")), esc(C.DIMENSION_NAMES.get(a.get("dimension"), "")))]
    strategies = "".join('<a class="chip" href="#swot">%s</a>' % esc(s) for s in a.get("strategy_ids") or [])
    extra = ""
    if full:
        extra += ('<div class="row-sub small">Priority %s = %s points x %s roles x %d%% chance / %s hours</div>'
                  % (esc(pr), esc(a.get("expected_points")), esc(a.get("roles_affected")),
                     round(float(a.get("chance", 0)) * 100), esc(a.get("effort_hours"))))
        extra += '<div class="row-sub small">Done when: %s</div>' % esc(a.get("done_when", ""))
        if a.get("done_evidence"):
            extra += '<div class="row-sub small">Evidence: %s</div>' % esc(a["done_evidence"])
        if a.get("draft"):
            extra += '<div class="row-sub small">Draft for you to send: %s</div>' % esc(a["draft"])
    if a.get("id") in stale:
        extra += ('<div class="flag">%s<span>No score or metric movement in %d runs. Rework or drop it, and log why.</span></div>'
                  % (icon("warn", 14), stale[a["id"]]))
    return ('<div class="row" id="act-%s"><div class="check %s"></div><div class="row-main">'
            '<div class="row-title">%s %s</div><div class="row-sub">%s</div>'
            '<div class="row-sub small">%s %s</div>%s</div></div>'
            % (esc(a.get("id")), esc(a.get("status")), esc(a.get("title")), status_pill(a.get("status")),
               esc(a.get("why", "")), " &middot; ".join(meta), strategies, extra))


def view_overview(data, stale):
    cur, outlook = data.cur, data.cur["outlook"]
    horizon = (data.config.get("goal") or {}).get("horizon_months", 12)
    t5, t5p = top5_avg(cur), (top5_avg(data.prev) if data.prev else None)
    n = cur["counts"]
    cards = ""
    for oid in data.targets:
        b = cur["per_org"].get(oid)
        c = data.colours[oid]
        head = '<div class="org-name"><i class="lkey" style="--c:%s;--cd:%s"></i>%s</div>' % (c[0], c[1], esc(data.org(oid)))
        if not b:
            cards += '<div class="card">%s<div class="muted small">No matching open role right now.</div></div>' % head
            continue
        cards += ('<div class="card">%s<div class="org-role">%s</div><div class="kv"><span>Fit</span><strong class="num">%s</strong></div>'
                  '<div class="kv"><span>Interview</span>%s</div><div class="kv"><span>Offer</span>%s</div></div>'
                  % (head, esc(b["title"]), esc(round(b["fit"])), band_pill(b["interview_band"]), band_pill(b["offer_band"])))
    today = "".join(action_row(a, data, stale, full=False) for a in data.active[:3]) or \
        '<div class="row muted">No open actions. The next run adds some from the biggest gaps.</div>'
    prev_m = data.metrics_history[-2]["metrics"] if len(data.metrics_history) > 1 else {}
    tiles = ""
    for m in data.plan.get("north_star", []):
        pv = prev_m.get(m["id"])
        tiles += ('<div class="tile"><div class="tile-label">%s</div><div class="tile-value">%s<span class="muted"> / %s</span></div>'
                  '<div class="small">%s</div></div>' % (esc(m["name"]), esc(m["current"]), esc(m["target"]),
                                                         "" if pv is None else delta(m["current"], pv)))
    attention = []
    if n.get("awaiting_review"):
        attention.append("%d roles have scores above 2 waiting for the sceptical reviewer, so they count as 2 for now."
                         % n["awaiting_review"])
    if n.get("not_judged"):
        attention.append("%d roles are not judged yet and score 0 on D1, D2 and D4." % n["not_judged"])
    if stale:
        attention.append("%d actions show no movement after 3 or more runs: rework or drop them." % len(stale))
    pending = sum(1 for c in data.claims if c.get("status") == "pending")
    if pending:
        attention.append("%d public claims are waiting to be checked against your evidence." % pending)
    for w in cur.get("warnings", [])[:5]:
        attention.append(w)
    attn = "" if not attention else ('<h2>Needs attention</h2><div class="card">' + "".join(
        '<div class="flag">%s<span>%s</span></div>' % (icon("warn", 14), esc(t)) for t in attention) + "</div>")
    return """
<div class="grid2">
  <div class="card"><div class="tile-label">Chance of reaching the goal within %s months, if the campaign is followed</div>
    <div class="hero-num">%s</div><p>%s</p><ul class="small">%s</ul></div>
  <div class="card"><div class="tile-label">Average fit of your 5 best roles, out of 100</div>
    <div class="hero-num num">%s</div><div>%s</div>
    <p class="muted small">%d open roles scored on %s. %d judged, %d waiting for review.</p></div>
</div>
<h2>Best chance at each organisation</h2><div class="grid3">%s</div>
<h2>Today's actions</h2><div class="list">%s</div>
<h2>Campaign scoreboard</h2><div class="grid3">%s</div>%s""" % (
        esc(horizon), esc(outlook["band"]), esc(outlook["text"]),
        "".join("<li>%s</li>" % esc(x) for x in outlook.get("reasons", [])),
        esc(round(t5)), delta(t5, t5p), n["roles"], esc(cur["run_date"]), n["judged"], n["awaiting_review"],
        cards, today, tiles, attn)


def view_trends(data):
    dates = [r["run_date"] for r in data.runs]
    s1 = A.PALETTE[0]
    out = line_chart("t5", "Average fit of your 5 best roles", dates,
                     [{"name": "Top 5 average", "values": [top5_avg(r) for r in data.runs], "colour": s1}])
    series = []
    for oid in data.targets:
        vals = [((r.get("per_org") or {}).get(oid) or {}).get("fit") for r in data.runs]
        if any(v is not None for v in vals):
            series.append({"name": data.org(oid), "values": vals, "colour": data.colours[oid]})
    out += line_chart("orgs", "Best role fit at each organisation", dates, series)
    if data.snapshots:
        sdates = [s["date"] for s in data.snapshots]
        counts = []
        for oid in data.targets:
            vals = [sum(1 for r in s.get("roles", {}).values() if r.get("org") == oid) for s in data.snapshots]
            counts.append({"name": data.org(oid), "values": vals, "colour": data.colours[oid]})
        top = max([v for s in counts for v in s["values"]] + [4])
        summ = data.roles_doc.get("summary") or {}
        new_ids, closed = summ.get("new_role_ids") or [], summ.get("closed_role_ids") or []
        note = ""
        if summ.get("previous_snapshot"):
            items = "".join("<li>New: %s, %s</li>" % (esc(data.role_index.get(i, {}).get("title", i)),
                                                      esc(data.org(i.split(":", 1)[0]))) for i in new_ids[:8])
            note = ("<p class='small muted'>Since %s: %d new and %d closed matching roles.</p><ul class='small'>%s</ul>"
                    % (esc(summ["previous_snapshot"]), len(new_ids), len(closed), items))
        out += line_chart("vel", "Open matching roles at each organisation", sdates, counts, ymax=top, note=note)
    avgs = dim_avgs(data.cur)
    w = data.cur.get("weights") or C.DEFAULT_WEIGHTS
    out += bar_chart("Where your 5 best roles score, by factor (out of 5)",
                     [{"label": "%s %s" % (d, C.DIMENSION_NAMES[d]), "value": avgs[d], "sub": "weight %s" % w.get(d)}
                      for d in C.DIMENSIONS], 5)
    if data.prev and data.prev.get("weights") != data.cur.get("weights"):
        out += '<div class="flag">%s<span>The weights changed since the last run, so fit scores before and after are not directly comparable.</span></div>' % icon("warn", 14)
    tiles = ""
    mdates = [m["date"] for m in data.metrics_history]
    for i, m in enumerate(data.plan.get("north_star", [])):
        vals = [h["metrics"].get(m["id"]) for h in data.metrics_history]
        top = max([v for v in vals if v is not None] + [m.get("target", 1), 1])
        tiles += line_chart("m%d" % i, "%s (target %s)" % (m["name"], m["target"]), mdates,
                            [{"name": m["name"], "values": vals, "colour": s1}], ymax=top, compact=True)
    if tiles:
        out += '<h2>Campaign metrics over time</h2><div class="grid3">%s</div>' % tiles
    return out


def view_roles(data):
    run = data.cur
    org_opts = "".join('<option value="%s">%s</option>' % (esc(o), esc(data.org(o))) for o in data.targets)
    fam_opts = "".join('<option value="%s">%s</option>' % (esc(f), esc(n)) for f, n in data.fam_names.items())
    rows = ""
    for r in run["roles"]:
        src = data.role_index.get(r["role_id"], {})
        dims = ""
        for d in C.DIMENSIONS:
            s = r["scores"][d]
            raw = "" if s["raw"] == s["score"] else ' <span class="muted small">(judged %d)</span>' % s["raw"]
            cap = '<div class="muted small">Capped: %s</div>' % esc(s["capped"]) if s.get("capped") else ""
            dims += ("<tr><td class='lead'>%s %s</td><td class='num'>%d/5%s</td><td>%s%s<div>%s</div></td></tr>"
                     % (d, esc(C.DIMENSION_NAMES[d]), s["score"], raw, esc(s["note"]), cap, ev_chips(s["evidence"], data)))
        blockers = "".join("<li>%s: %s</li>" % (esc(C.BLOCKER_NAMES.get(b["type"], b["type"])), esc(b["text"]))
                           for b in src.get("eligibility_blockers") or [])
        facts = []
        if src.get("compensation"):
            facts.append("Pay: %s" % src["compensation"])
        if src.get("years_experience") is not None:
            facts.append("Years asked for: %s (%s)" % (src["years_experience"], src.get("years_experience_basis")))
        if src.get("degree_requirement"):
            facts.append("Degree: %s" % src["degree_requirement"])
        body = ("<div class='tablewrap'><table class='dims stack'><tr class='head'><th>Factor</th><th class='num'>Score</th><th>Why</th></tr>%s</table></div>"
                % dims)
        body += "<p class='small'><strong>Fit %s</strong>, interview %s, offer %s.</p>" % (
            esc(r["fit"]), band_pill(r["interview_band"]), band_pill(r["offer_band"]))
        if r["adjustments"]:
            body += "<ul class='small'>%s</ul>" % "".join("<li>%s</li>" % esc(a) for a in r["adjustments"])
        if blockers:
            body += "<p class='small'><strong>Eligibility blockers in the posting</strong></p><ul class='small'>%s</ul>" % blockers
        if facts:
            body += "<p class='small muted'>%s</p>" % " &middot; ".join(esc(f) for f in facts)
        if r.get("reviewer_note"):
            body += "<p class='small'><strong>Reviewer:</strong> %s</p>" % esc(r["reviewer_note"])
        if r.get("url"):
            body += "<p class='small'><a href='%s' rel='noopener noreferrer'>Open the job posting</a></p>" % esc(r["url"])
        text = " ".join([r["title"], data.org(r["org"]), " ".join(r.get("locations") or [])]).lower()
        rows += ('<details class="rrow" data-org="%s" data-family="%s" data-blocked="%s" data-text="%s"><summary>'
                 '<span class="rtitle">%s<span class="row-sub">%s &middot; %s &middot; %s</span></span>'
                 '<span class="rscore">%s</span>%s</summary><div class="rbody">%s</div></details>'
                 % (esc(r["org"]), esc(r["family"]), "1" if r["eligibility_blocked"] else "0", esc(text),
                    esc(r["title"]), esc(data.org(r["org"])), esc(data.fam(r["family"])),
                    esc(", ".join((r.get("locations") or [])[:2]) or "Location not listed"),
                    esc(round(r["fit"])), band_pill(r["interview_band"]), body))
    if not rows:
        rows = '<div class="row muted">No roles yet. Run scripts/fetch_roles.py and scripts/score.py.</div>'
    return ("""<div class="toolbar"><input type="search" id="f-q" placeholder="Search roles" aria-label="Search roles">
<select id="f-org" aria-label="Organisation"><option value="">All organisations</option>%s</select>
<select id="f-fam" aria-label="Role type"><option value="">All role types</option>%s</select>
<label><input type="checkbox" id="f-blocked"> Hide blocked</label><span id="f-count" class="muted small"></span></div>
<div class="list" id="roles">%s</div>""" % (org_opts, fam_opts, rows))


def roles_moved(item, quad, run, top_n):
    top = run["roles"][:top_n]
    orgs, fams = item.get("orgs", "all"), item.get("families", "all")
    pool = [r for r in top if (orgs == "all" or r["org"] in orgs) and (fams == "all" or r["family"] in fams)]
    d = item["dimension"]
    hit = [r for r in pool if (r["scores"][d]["score"] >= 3 if quad == "strengths" else r["scores"][d]["score"] <= 2)]
    return len(hit), len(pool)


def swot_grid(grid, data, top_n, scope):
    quads = [("strengths", "Strengths", "Internal, helps", "plus"), ("weaknesses", "Weaknesses", "Internal, hurts", "minus"),
             ("opportunities", "Opportunities", "External, helps", "up"), ("threats", "Threats", "External, hurts", "warn")]
    out = ""
    for key, label, kind, ic in quads:
        items = ""
        for it in grid.get(key, []):
            meta = []
            if it.get("dimension"):
                meta.append("Feeds %s %s" % (it["dimension"], C.DIMENSION_NAMES[it["dimension"]]))
            if key in ("strengths", "weaknesses"):
                n, of = roles_moved(it, key, data.cur, top_n)
                meta.append("%s %d of the %d best roles in scope" % ("helps" if key == "strengths" else "holds back", n, of))
                src = ev_chips(it.get("evidence"), data)
            else:
                src = '<span class="muted small">Source: %s</span>' % esc(it.get("source", ""))
            items += ('<div class="qitem"><span class="qid">%s</span>%s<div class="row-sub small">%s</div><div>%s</div></div>'
                      % (esc(it["id"]), esc(it["text"]), " &middot; ".join(esc(m) for m in meta), src))
        out += ('<div class="quad"><div class="quad-head">%s<strong>%s</strong><span class="quad-kind">%s</span></div>%s</div>'
                % (icon(ic, 18), label, kind, items or '<div class="muted small">None recorded yet.</div>'))
    intel = ""
    if scope != "overall":
        info = data.orgs_intel.get(scope) or {}
        bits = ["<li>Office: %s</li>" % esc(o) for o in info.get("offices", [])]
        bits += ["<li>%s <span class='muted small'>(%s)</span></li>" % (esc(f["text"]), esc(f["source"]))
                 for f in info.get("facts", [])]
        if bits:
            intel = '<div class="card"><h3>What we know about %s</h3><ul class="small">%s</ul></div>' % (
                esc(data.org(scope)), "".join(bits))
    return '<div class="swot">%s</div>%s' % (out, intel)


def view_swot(data):
    if not data.swot:
        return '<div class="card muted">No SWOT yet. The agent writes eval/swot.json after the first scored run (method/SWOT.md).</div>'
    top_n = int(((data.config.get("scoring") or {}).get("top_n_for_gaps")) or 25)
    scopes = [("overall", "Overall", data.swot.get("overall") or {})]
    for oid in data.targets:
        if oid in (data.swot.get("per_org") or {}):
            scopes.append((oid, data.org(oid), data.swot["per_org"][oid]))
    buttons = "".join('<button type="button" data-scope="%s" class="%s" aria-pressed="%s">%s</button>'
                      % (esc(s), "on" if i == 0 else "", "true" if i == 0 else "false", esc(label))
                      for i, (s, label, _) in enumerate(scopes))
    panels = "".join('<div class="swot-scope%s" id="scope-%s"><h3 class="muted">%s</h3>%s</div>'
                     % (" on" if i == 0 else "", esc(s), esc(label), swot_grid(g, data, top_n, s))
                     for i, (s, label, g) in enumerate(scopes))
    texts = {}
    for _, _, g in scopes:
        for quad in ("strengths", "weaknesses", "opportunities", "threats"):
            for it in g.get(quad, []):
                texts[it["id"]] = it["text"]
    blocks = ""
    for kind, label, explain in TOWS:
        items = ""
        for s in [x for x in data.swot.get("strategies", []) if x.get("type") == kind]:
            uses = "".join('<span class="chip" title="%s">%s</span>' % (esc(texts.get(u, "")), esc(u)) for u in s["uses"])
            links = "".join('<a href="#plan/%s">%s %s</a>' % (esc(aid), esc(aid), esc(
                data.action_index.get(aid, {}).get("title", "(not in the plan)"))) for aid in s.get("actions", []))
            scope = s.get("scope") or "overall"
            items += ('<div class="strategy"><span class="qid">%s</span>%s<div class="row-sub small">Uses %s &middot; Scope: %s</div>'
                      '<div class="links small">Plan actions: %s</div></div>'
                      % (esc(s["id"]), esc(s["text"]), uses, esc("Overall" if scope == "overall" else data.org(scope)),
                         links or '<span class="muted">none yet</span>'))
        blocks += ('<div class="card"><h3>%s (%s)</h3><p class="muted small">%s</p>%s</div>'
                   % (label, kind, explain, items or '<div class="muted small">No strategy of this type yet.</div>'))
    return ('<div class="scope" role="group" aria-label="SWOT scope">%s</div>%s<h2>TOWS strategies: turning the grid into moves</h2>'
            '<div class="grid2">%s</div>' % (buttons, panels, blocks))


def view_plan(data, stale):
    gaps = data.cur.get("gaps", [])
    by_gap = {}
    for a in data.actions:
        if a.get("gap_id"):
            by_gap.setdefault(a["gap_id"], []).append(a["id"])
    out = bar_chart("What would lift your odds most (fit points gained, summed over your best roles)",
                    [{"label": g["title"], "value": g["points_gain"],
                      "sub": "%d roles, %s%s" % (g["roles_affected"], g["dimension"],
                                                 (", actions " + ", ".join(by_gap[g["id"]])) if g["id"] in by_gap else "")}
                     for g in gaps], max([g["points_gain"] for g in gaps] or [1]), " pts")
    cap = int(data.plan.get("max_active", 8))
    out += '<h2>Active actions, by priority (%d of %d allowed)</h2><div class="list">%s</div>' % (
        len(data.active), cap, "".join(action_row(a, data, stale) for a in data.active) or
        '<div class="row muted">None.</div>')
    cols = ""
    for status in ("doing", "todo", "done", "dropped"):
        items = [a for a in data.actions if a.get("status") == status]
        cols += ('<div class="card"><div class="tile-label">%s (%d)</div>%s</div>'
                 % (STATUS_LABEL[status], len(items), "".join(
                     '<div class="kitem"><a href="#plan/%s" class="row-title" style="color:inherit;text-decoration:none">%s</a>'
                     '<div class="row-sub small">%s</div></div>' % (esc(a["id"]), esc(a["title"]), esc(
                         a.get("done_evidence") or "%s h, %s" % (a.get("effort_hours"), a.get("owner", "you"))))
                     for a in items) or '<div class="muted small">None</div>'))
    out += '<h2>Board</h2><div class="grid4">%s</div>' % cols
    done_drop = [a for a in data.actions if a.get("status") in ("done", "dropped")]
    if done_drop:
        out += '<h2>Finished and dropped</h2><div class="list">%s</div>' % "".join(action_row(a, data, stale) for a in done_drop)
    exp = data.plan.get("experiments_log", [])
    rows = "".join("<tr><td class='num'>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        esc(e.get("date")), esc(e.get("action") or e.get("action_id")), esc(e.get("result")), esc(e.get("decision")),
        esc(e.get("why", ""))) for e in exp)
    out += ("<h2>What we tried, and what we kept</h2><div class='card'>" + (
        "<div class='tablewrap'><table class='dims'><tr><th>Date</th><th>Action</th><th>Result</th><th>Decision</th><th>Why</th></tr>%s</table></div>" % rows
        if rows else "<p class='muted'>Nothing tried yet. This fills in as actions finish or get dropped.</p>") + "</div>")
    if data.plan.get("backlog"):
        out += "<h2>Backlog</h2><div class='card'><ul>%s</ul></div>" % "".join(
            "<li>%s</li>" % esc(b) for b in data.plan["backlog"])
    return out


def view_evidence(data):
    items = data.evidence.get("items", [])
    counts = {}
    for e in items:
        counts[e.get("level")] = counts.get(e.get("level"), 0) + 1
    out = '<div class="grid3">%s</div>' % "".join(
        '<div class="tile"><div class="tile-label">%s</div><div class="tile-value">%d</div></div>' % (label, counts.get(k, 0))
        for k, label in LEVELS)
    verify = "".join("<li><strong>%s</strong> <span class='muted'>%s</span></li>" % (esc(v["question"]), esc(v["why"]))
                     for v in data.cur.get("verify_to_unlock", []))
    out += '<h2>Questions only you can answer</h2><div class="card"><ul>%s</ul></div>' % (
        verify or "<li class='muted'>None right now.</li>")
    if data.claims:
        ccount = {}
        for c in data.claims:
            ccount[c["status"]] = ccount.get(c["status"], 0) + 1
        flagged = [c for c in data.claims if c["status"] in ("overstated", "unsupported", "contradicted")]
        rows = "".join("<div class='kitem'><span class='tag t-%s'>%s</span> %s<div class='row-sub small'>Honest wording: %s</div>"
                       "<div class='muted small'>%s</div></div>" % (esc(c["status"]), esc(c["status"]), esc(c["text"]),
                                                                   esc(c.get("suggested_wording") or "not written yet"),
                                                                   esc(c["source"])) for c in flagged)
        out += ('<h2>Public claims audit</h2><div class="grid3">%s</div><div class="card"><h3>Fix these first</h3>%s</div>'
                % ("".join('<div class="tile"><div class="tile-label">%s</div><div class="tile-value">%d</div></div>'
                           % (label, ccount.get(k, 0)) for k, label in CLAIM_STATUSES),
                   rows or "<p class='muted small'>No overclaims found.</p>"))
    if data.network:
        names = bool(data.privacy.get("show_contact_names_in_dashboard"))
        cards = ""
        for oid in data.targets:
            org = (data.network.get("orgs") or {}).get(oid) or {"count": 0, "first_degree": []}
            people = "".join("<li>%s%s</li>" % (esc(c["name"] + ", ") if names else "", esc(c.get("position") or "position not listed"))
                             for c in org["first_degree"][:5])
            paths = [p for p in data.network.get("second_degree") or [] if p.get("org") == oid]
            path_txt = "".join("<li>Second-degree path%s: %s</li>" % (
                (" via " + esc(p["via"])) if names and p.get("via") else "", esc(p["status"])) for p in paths)
            cards += ('<div class="card"><div class="org-name">%s</div><div class="tile-value">%d</div>'
                      '<div class="tile-label">first-degree contacts</div><ul class="small">%s%s</ul></div>'
                      % (esc(data.org(oid)), org["count"], people, path_txt))
        out += '<h2>Your network at each organisation</h2><div class="grid3">%s</div>' % cards
        if not names:
            out += "<p class='muted small'>Names are hidden. Set privacy.show_contact_names_in_dashboard to true to show them here.</p>"
    groups = {}
    for e in items:
        groups.setdefault(e.get("kind", "other"), []).append(e)
    out += "<h2>All evidence</h2>"
    for kind in sorted(groups):
        rows = ""
        for i in groups[kind]:
            srcs = ", ".join(('<a href="%s" rel="noopener noreferrer">%s</a>' % (esc(s["ref"]), esc(s["type"].replace("_", " ")))
                              if re.match(r"^https?://", s["ref"]) else esc("%s: %s" % (s["type"].replace("_", " "), s["ref"])))
                             for s in i.get("sources", []))
            rows += ("<tr><td class='num'>%s</td><td class='lead-tag'><span class='tag t-%s'>%s</span></td><td>%s<div class='muted small'>%s</div>"
                     "<div class='muted small'>Feeds %s</div></td></tr>" % (
                         esc(i["id"]), esc(i["level"]), esc(i["level"].replace("_", " ")), esc(i["claim"]), srcs,
                         esc(", ".join(i.get("dimensions") or []) or "no dimension")))
        out += ('<details class="card"><summary>%s (%d)</summary><div class="tablewrap"><table class="dims stack">%s</table></div></details>'
                % (esc(kind.replace("_", " ").capitalize()), len(groups[kind]), rows))
    if not items:
        out += '<div class="card muted">No evidence yet. The intake (method/INTAKE.md) fills this in.</div>'
    return out


def render_page(data):
    stale = stale_actions(data)
    cfg, cur = data.config, data.cur
    report = cfg.get("report") or {}
    goal = cfg.get("goal") or {}
    title = report.get("title") or "Career campaign"
    subtitle = " ".join(x for x in [goal.get("title", "") + ".", report.get("subtitle", "")] if x.strip(". "))
    cadence = (cfg.get("cadence") or {}).get("mode", "daily")
    banner = ""
    if cfg.get("fictional"):
        banner = ('<div class="banner">Demo with made-up data. %s and every organisation, role and contact here are '
                  'fictional.</div>' % esc((cfg.get("candidate") or {}).get("display_name") or "This person"))
    views = [("overview", "Overview", view_overview(data, stale)), ("trends", "Trends", view_trends(data)),
             ("roles", "Roles", view_roles(data)), ("swot", "SWOT", view_swot(data)),
             ("plan", "Plan", view_plan(data, stale)), ("evidence", "Evidence", view_evidence(data))]
    if not data.privacy.get("show_contact_names_in_dashboard"):
        hide = make_redactor(data, sensitive=False, hide_names=True)
        views = [(v, label, hide(body)) for v, label, body in views]
    nav = "".join('<a href="#%s">%s</a>' % (v, label) for v, label, _ in views)
    sections = "".join('<section class="view" id="v-%s" aria-label="%s"><h2 class="view-title">%s</h2>%s</section>'
                       % (v, label, label, body) for v, label, body in views)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="robots" content="noindex">
<title>%s</title><script>document.documentElement.className += " js";</script>
<style>%s</style></head><body><div class="wrap">
<div class="muted small">Private &middot; last run %s &middot; rubric %s &middot; %s runs</div>
<h1>%s</h1><div class="muted">%s</div>%s
<nav class="seg" aria-label="Views">%s</nav>
%s
<p class="foot">How scores work: seven factors, each scored 0 to 5 from cited evidence, weighted into a fit score out of 100,
then turned into chance bands. A separate sceptical reviewer must agree with every score above 2. Bands are judgement, not
statistics. Rules: method/RUBRIC.md in the career-eval engine. Drafts only: the engine never applies, sends, posts or changes accounts.</p>
</div><div class="tip" id="tip" role="status"></div>
<script>%s</script></body></html>
""" % (esc(title), A.CSS, esc(cur["run_date"]), esc(cur["rubric_version"]), esc(cadence), esc(title), esc(subtitle),
       banner, nav, sections, A.JS)

# ------------------------------------------------------------ agent files


MONEY_RX = re.compile(r"(?:[$\u00a3\u20ac]\s?|\b(?:USD|AUD|EUR|GBP|CAD|NZD|SGD)\s?)\d[\d,.]*\s?[kKmM]?\b"
                      r"(?:\s*(?:to|-|\u2013|\u2014)\s*(?:[$\u00a3\u20ac]\s?)?\d[\d,.]*\s?[kKmM]?\b)?")


def make_redactor(data, sensitive, hide_names):
    """Return a function that cleans one string for the agent files.

    Contact names are hidden unless the person opted in; redact_terms and money
    amounts are hidden in sensitive mode."""
    terms = [t for t in data.privacy.get("redact_terms") or [] if t.strip()] if sensitive else []
    names = set()
    for org in ((data.network or {}).get("orgs") or {}).values():
        for c in org.get("first_degree", []):
            if c.get("name"):
                names.add(c["name"])
    for p in (data.network or {}).get("second_degree") or []:
        for k in ("via", "target_person"):
            if p.get(k):
                names.add(p[k])
    if not hide_names:
        names = set()
    names |= {esc(n) for n in names}  # also catch names as they appear in escaped HTML
    rules = [(re.compile(r"(?<!\w)%s(?!\w)" % re.escape(t), re.I), "[redacted]") for t in sorted(terms, key=len, reverse=True)]
    rules += [(re.compile(r"(?<!\w)%s(?!\w)" % re.escape(n), re.I), "[contact]") for n in sorted(names, key=len, reverse=True)]

    def clean(text):
        for rx, sub in rules:
            text = rx.sub(sub, text)
        return MONEY_RX.sub("[salary]", text) if sensitive else text
    return clean


def scrub(value, clean):
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, list):
        return [scrub(v, clean) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v, clean) for k, v in value.items() if k != "compensation"}
    return value


def agent_payload(data):
    sensitive = bool(data.privacy.get("sensitive_mode", True))
    share_names = bool(data.privacy.get("share_contact_names_with_agents")) and not sensitive
    cur, goal = data.cur, data.config.get("goal") or {}
    counts = {}
    for e in data.evidence.get("items", []):
        counts[e.get("level")] = counts.get(e.get("level"), 0) + 1
    payload = {
        "about": "Private career campaign data. Read only. See SUMMARY.md in this folder for the rules.",
        "generated_by": "career-eval scripts/build_dashboard.py",
        "sensitive_mode": sensitive,
        "run_date": cur["run_date"], "rubric_version": cur["rubric_version"],
        "goal": {"title": goal.get("title", ""), "description": goal.get("description", ""),
                 "horizon_months": goal.get("horizon_months", 12)},
        "outlook": cur["outlook"],
        "top5_average_fit": top5_avg(cur),
        "top5_average_fit_previous": top5_avg(data.prev) if data.prev else None,
        "per_org": {o: (dict(b, org_name=data.org(o)) if b else None) for o, b in cur["per_org"].items()},
        "gaps": cur.get("gaps", []),
        "verify_to_unlock": cur.get("verify_to_unlock", []),
        "actions_active": [dict(a, priority=priority(a)) for a in data.active],
        "actions_done": [a for a in data.actions if a.get("status") == "done"],
        "north_star": data.plan.get("north_star", []),
        "metrics_history": data.metrics_history,
        "evidence_counts": counts,
        "claims_audit_counts": {k: sum(1 for c in data.claims if c["status"] == k) for k, _ in CLAIM_STATUSES},
        "network_first_degree_counts": {o: v.get("count", 0) for o, v in ((data.network or {}).get("orgs") or {}).items()},
        "roles": [{"role_id": r["role_id"], "org": r["org"], "title": r["title"], "family": r["family"],
                   "locations": r.get("locations", []), "url": r.get("url"), "fit": r["fit"],
                   "interview_band": r["interview_band"], "offer_band": r["offer_band"],
                   "scores": {d: r["scores"][d]["score"] for d in C.DIMENSIONS},
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
    if sensitive or not share_names:
        clean = make_redactor(data, sensitive, hide_names=not share_names)
        payload = scrub(payload, clean) if sensitive else _scrub_text(payload, clean)
    return payload


def _scrub_text(value, clean):
    """Like scrub, but keeps every field (used when only contact names are hidden)."""
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, list):
        return [_scrub_text(v, clean) for v in value]
    if isinstance(value, dict):
        return {k: _scrub_text(v, clean) for k, v in value.items()}
    return value


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
        "%s. %s" % (p["goal"]["title"], p["goal"]["description"]),
        "",
        "## Outlook",
        "- Chance of reaching the goal within %s months if the campaign is followed: %s" % (
            p["goal"]["horizon_months"], p["outlook"]["band"]),
        "- %s" % p["outlook"]["text"],
        "- Average fit of the 5 best open roles: %s / 100%s" % (
            p["top5_average_fit"],
            "" if p["top5_average_fit_previous"] is None else " (previous run %s)" % p["top5_average_fit_previous"]),
        "",
        "## Best role at each organisation",
    ]
    for oid, b in p["per_org"].items():
        lines.append("- %s: %s" % (data.org(oid), "%s, fit %s, interview %s, offer %s" % (
            b["title"], round(b["fit"]), b["interview_band"], b["offer_band"]) if b else "no matching open role"))
    lines += ["", "## Active actions (highest priority first)"]
    for a in p["actions_active"]:
        lines.append("- [%s] %s %s (owner: %s; done when: %s)" % (a["status"], a["id"], a["title"], a.get("owner", "you"),
                                                                 a.get("done_when", "")))
    lines += ["", "## Biggest gaps"]
    for g in p["gaps"]:
        lines.append("- %s: +%s fit points across %d roles. %s" % (g["title"], g["points_gain"], g["roles_affected"], g["why"]))
    lines += ["", "## Top 10 open roles"]
    for r in p["roles"][:10]:
        lines.append("- %s  %s: %s (interview %s, offer %s) %s" % (round(r["fit"]), data.org(r["org"]), r["title"],
                                                                  r["interview_band"], r["offer_band"], r.get("url") or ""))
    lines += ["", "## Questions only the person can answer"]
    for v in p["verify_to_unlock"]:
        lines.append("- %s (%s)" % (v["question"], v["why"]))
    lines += ["", "## Evidence and network",
              "- Evidence items by level: %s" % (", ".join("%s %d" % (k, v) for k, v in sorted(p["evidence_counts"].items())) or "none"),
              "- First-degree contacts per organisation: %s" % (", ".join(
                  "%s %d" % (data.org(o), n) for o, n in p["network_first_degree_counts"].items()) or "not mapped yet")]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the dashboard and the agent briefing.")
    ap.add_argument("--workspace", help="workspace folder (default: $CAREER_EVAL_HOME)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    data = Data(ws, config)
    update_metrics_history(data)
    C.write_text(C.wpath(ws, "report", "index.html"), render_page(data))
    payload = agent_payload(data)
    C.write_json(C.wpath(ws, "report", "for-agents", "dashboard.json"), payload)
    C.write_text(C.wpath(ws, "report", "for-agents", "SUMMARY.md"), summary_md(data, payload))
    print("Wrote report/index.html, report/for-agents/SUMMARY.md, report/for-agents/dashboard.json "
          "(sensitive mode %s)" % ("on" if payload["sensitive_mode"] else "off"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
