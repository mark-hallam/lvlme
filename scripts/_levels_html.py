"""The level-up view and the hero's level card, rendered once in Python for the static page.

The page script renders the same markup again on load (so the what-if switches
and the organisation selector can change it); this first render means the next
level, the quests and the level history are readable even with JavaScript off.
It follows the best role overall with every open action switched on, which is
also what the agent briefing reports. Keep the markup in step with JS_LEVELS in
_dashboard_assets.py.
"""
import datetime as dt
import html

import _levels as L

STATUS = {"doing": "In progress", "later": "Parked for later", "done": "Done", "dropped": "Dropped"}


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def fp(v):
    """A fit-point number as the page shows it: one decimal, none if whole."""
    return "%g" % L.r1(v)


def long_date(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, d.strftime("%b"), d.year)


def short(iso):
    d = dt.date.fromisoformat(iso)
    return "%d %s" % (d.day, d.strftime("%b"))


def plural(n, one, many=None):
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def and_list(xs):
    return "".join(xs) if len(xs) < 2 else ", ".join(xs[:-1]) + " and " + xs[-1]


def cap1(s):
    return s[:1].upper() + s[1:] if s else ""


def compute(page):
    """The next level and the quests for the best role overall, every open action on."""
    r, acts, today = page["roles"][0], page["actions"], page["meta"]["run_date"]
    nl = L.next_level(r, acts, page["caps"], page["weights"], today)
    return r, nl, L.quests(r, acts, page["caps"], page["weights"], nl)


def nl_line(nl, today):
    if nl["top"]:
        return "Top level. Keep the evidence fresh so it stays there."
    if nl["reachable"]:
        s, n = nl["set"], len(nl["set"]["ids"])
        when = "today" if s["date"] == today else "by " + short(s["date"])
        return "Level %d expected %s if %s on time." % (nl["next_level"], when, "1 action lands" if n == 1 else "%d actions land" % n)
    return "Level %d isn't reached on the current plan: %s points short, counting each action's chance." % (
        nl["next_level"], fp(nl["missing"]["points"]))


def level_card(page, nl):
    lv, today = nl["level"] - 1, page["meta"]["run_date"]
    lo, hi = L.THRESH[lv], L.THRESH[lv + 1]
    width = max(0.0, min(100.0, (nl["fit"] - lo) / float(hi - lo) * 100))
    changes = [h for h in L.level_history(page["runs"]) if h["change"]]
    to_next = "Top level" if nl["top"] else "%s %s to Level %d, %s" % (
        fp(nl["points_to_next"]), "point" if nl["points_to_next"] == 1 else "points", nl["next_level"], esc(nl["next_band"]))
    ch = changes[-1] if changes else None
    return ('<div class="level-top"><div class="level-badge">%d</div><div><div class="level-name">Level %d, %s</div>'
            '<div class="tiny sub">%s</div></div></div><div class="prog"><span style="width:%s%%"></span></div>'
            '<div class="tiny lv-line">%s</div>%s') % (
        nl["level"], nl["level"], esc(nl["band"]), to_next, "%g" % width, esc(nl_line(nl, today)),
        '<div class="tiny sub" style="margin-top:2px">%s %s, %s to %s</div>' % (
            "Levelled up" if ch["change"] == "up" else "Dropped a level", long_date(ch["date"]),
            esc(L.BANDS[ch["from_level"] - 1]), esc(ch["band"])) if ch else "")


def _steps(acts):
    rows = "".join('<div class="lv-step"><span class="tag crit">%s</span><span class="lv-step-t">%s</span>'
                   '<span class="tiny sub">%s · %d%% chance</span></div>' % (
                       esc(a["id"]), esc(a["title"]), "by " + short(a["date"]) if a.get("dated") else "no date yet", L.pct(a["p"]))
                   for a in acts)
    return '<div class="lv-set">%s</div>' % rows


def _track(nl):
    idx, t = nl["level"] - 1, nl["target"]
    lo, hi = L.THRESH[idx], L.THRESH[idx + 2]

    def at(v):
        return "%g" % max(0.0, min(100.0, (v - lo) / float(hi - lo) * 100))
    now, ex, be, g = (float(at(v)) for v in (nl["fit"], nl["plan"]["fit_expected"], nl["plan"]["fit_best"], t))
    return ('<div class="lv-track" role="img" aria-label="Today %s. Expected with the plan %s. Best case %s. Level %d starts at %d.">'
            '<div class="lv-zone" style="left:%g%%"></div><div class="lv-base"></div><div class="lv-fill" style="width:%g%%"></div>'
            '<div class="lv-exp" style="left:%g%%;width:%g%%"></div><div class="lv-bx" style="left:%g%%;width:%g%%"></div>'
            '<div class="lv-goal" style="left:%g%%"></div><span class="lv-mk best" style="left:%g%%"></span>'
            '<span class="lv-mk exp" style="left:%g%%"></span><span class="lv-mk now" style="left:%g%%"></span></div>'
            '<div class="lv-axis"><span style="left:0;transform:none">%d</span><span class="goal" style="left:%g%%">Level %d at %d</span>'
            '<span style="left:100%%;transform:translateX(-100%%)">%d</span></div>'
            '<div class="legend lv-legend"><span><i class="p90-key" style="background:var(--ink)"></i>Today %s</span>'
            '<span><i class="lv-key exp"></i>Expected with the plan %s</span><span><i class="lv-key best"></i>Best case %s</span></div>') % (
        fp(nl["fit"]), fp(nl["plan"]["fit_expected"]), fp(nl["plan"]["fit_best"]), nl["next_level"], t,
        g, now, now, max(0.0, ex - now), ex, max(0.0, be - ex), g, be, ex, now, lo, g, nl["next_level"], t, hi,
        fp(nl["fit"]), fp(nl["plan"]["fit_expected"]), fp(nl["plan"]["fit_best"]))


def _chance(found, lead):
    if found.get("chance") is None:
        return ""
    return '<p class="small sub">%s%d%%%s.</p>' % (lead, L.pct(found["chance"]),
                                                  ", treating each action's chance as independent" if len(found["acts"]) > 1 else "")


def verdict(page, nl):
    if nl["top"]:
        return ('<div class="lv-verdict"><div class="lv-v-h">Top level</div><p class="small">Strong is the highest band. '
                'The work now is keeping the evidence fresh and the warm paths warm.</p></div>')
    lvl = "Level %d (%s)" % (nl["next_level"], esc(nl["next_band"]))
    if nl["reachable"]:
        s = nl["set"]
        n = len(s["acts"])
        out = ['<div class="lv-verdict"><div class="lv-v-h">%s can get you there</div>' % ("One action" if n == 1 else "%d actions" % n),
               '<p class="small">If %s, you\'re expected to reach %s on <b>%s</b>, at a fit of %s counting each action\'s chance of working.</p>' % (
                   "it lands on its target date" if n == 1 else "they land on their target dates", lvl, long_date(s["date"]), fp(s["fit"])),
               _chance(s, "Chance it really happens: ")]
        if nl["plan"]["date"] and nl["plan"]["date"] < s["date"]:
            out.append('<p class="small sub">Doing everything switched on in the plan is expected to get there sooner, on %s.</p>'
                       % long_date(nl["plan"]["date"]))
        if not s["exact"]:
            out.append('<p class="small sub">The plan is long, so this set comes from a quick search; a smaller one may exist.</p>')
        return "".join(out) + _steps(s["acts"]) + "</div>"
    m, bc = nl["missing"], nl.get("best_case")
    out = ['<div class="lv-verdict"><div class="lv-v-h">Not reachable on the current plan</div>',
           '<p class="small">Counting each action\'s chance of working, no set of your switched-on actions reaches %s. All of them together '
           'are expected to take this role to %s, which is <b>%s points short</b>.</p>' % (lvl, fp(nl["plan"]["fit_expected"]), fp(m["points"]))]
    if bc:
        k = len(bc["acts"])
        out.append('<p class="small"><b>Best case only:</b> %s together reach %s by %s, but only if %s.</p>' % (
            esc(and_list(bc["ids"])), fp(bc["fit"]), long_date(bc["date"]),
            "it works" if k == 1 else "both work" if k == 2 else "all of them work"))
        out.append(_chance(bc, "Chance of that: ") + _steps(bc["acts"]))
    else:
        out.append('<p class="small sub">Not even the best case gets there: if every action works, this role reaches %s.</p>'
                   % fp(nl["plan"]["fit_best"]))
    out.append('<div class="eyebrow" style="margin-top:16px">What is missing</div>')
    if m["ceiling"] < nl["target"]:
        out.append('<p class="small">Even with every factor at the most the plan\'s caps allow, this role tops out at %s. Reaching %s needs '
                   'something the caps rule out within this plan, such as more years in a similar role, or a different role.</p>'
                   % (fp(m["ceiling"]), lvl))
    else:
        out.append('<p class="small sub">Room left on this role within the plan\'s caps, in fit points, if new actions fully work. The %s '
                   'points have to come from here: add an action where none exists, or raise the odds of the ones you have.</p>' % fp(m["points"]))
    rows = "".join('<div class="lv-room"><span><b style="font-weight:600">%s</b><div class="tiny sub">%s</div></span><b class="num">+%s</b></div>' % (
        esc(page["dimNames"][x["dimension"]]), "Open actions cover part of it" if x["covered"] else "No open action raises it for this role",
        fp(x["points"])) for x in m["room"])
    out.append("<div>%s</div></div>" % (rows or '<div class="small sub">No room left within the caps.</div>'))
    return "".join(out)


def quest_card(q, nl):
    a = q["a"]
    tags = "".join([
        '<span class="tag crit">On the path to Level %d</span>' % nl["next_level"] if q["crit"] else "",
        '<span class="tag">Needed for the best case</span>' if not nl.get("reachable") and q["bc"] else "",
        '<span class="tag">Estimated effect</span>' if a.get("derived") else "",
        '<span class="tag pend">No movement in %d runs</span>' % a["stale"] if a.get("stale") else ""])
    if not a["effects"]:
        pts = '<span class="small sub">Protects credibility, no score change</span>'
    elif q["exp"] <= 0 and q["works"] <= 0:
        pts = '<span class="small sub">No points on this role</span>'
    else:
        pts = ('<span><b class="num">+%s</b> <span class="tiny sub">expected</span></span><span><b class="num q-alt">+%s</b> '
               '<span class="tiny sub">if it works</span></span><span class="tiny sub num">%s per hour</span>') % (fp(q["exp"]), fp(q["works"]), fp(q["rate"]))
    return ('<div class="quest%s"><div class="q-top"><div class="q-tags">%s</div><span class="q-id">%s · %s</span></div>'
            '<div class="q-title">%s</div><div class="q-pts">%s</div><div class="q-meta">%s%s · %s · %d%% chance</div>'
            '<div class="small"><span class="sub">Done when:</span> %s</div>'
            '<div class="q-foot small"><span><span class="sub">Done? Tell your agent:</span><span class="q-text">%s</span></span></div></div>') % (
        " crit" if q["crit"] else "", tags, esc(a["id"]), STATUS.get(a["status"], "To do"), esc(a["title"]), pts, esc(a["owner"]),
        " · " + esc(a["effort"]) if a.get("effort") else "", "due " + long_date(a["date"]) if a.get("dated") else "no due date yet",
        L.pct(a["p"]), esc(a.get("done_when")), esc(L.tell_agent(a)))


def _why(d):
    if not d:
        return ""
    if d["start"]:
        return "Day 1, measured."
    if not d["progress"]:
        return "No real progress that day."
    parts = ["fit rose on %s" % plural(d["roles_up"], "role") if d["roles_up"] else "",
             "newly checked evidence %s" % ", ".join(d["evidence"]) if d["evidence"] else "",
             "done with evidence: %s" % ", ".join(d["actions"]) if d["actions"] else ""]
    return cap1(" · ".join(p for p in parts if p)) + "."


def progress(page):
    days, n = page.get("progress") or [], page.get("streak") or 0
    by_date = {d["date"]: d for d in days}
    hist = list(reversed(L.level_history(page["runs"])))
    note = ("Day 1 is measured. The streak starts with the next scored day that shows real progress." if len(days) < 2
            else "The latest scored day showed no real progress, so the streak starts again." if not n
            else "Real progress means a score that rose, newly checked evidence, or an action done with evidence, on any role.")
    dots = "".join('<span class="sd%s" title="%s: %s"></span>' % (" start" if d["start"] else " on" if d["progress"] else "",
                                                                  long_date(d["date"]), esc(_why(d))) for d in days)
    rows = "".join('<div class="lh-row"><span class="tiny sub lh-date">%s</span><span class="lv-badge">%d</span><div><div class="small">'
                   '<b>Level %d, %s</b> · fit %d%s</div><div class="tiny sub">%s</div></div></div>' % (
                       long_date(h["date"]), h["level"], h["level"], esc(h["band"]), int(h["fit"] + 0.5),
                       ' <span class="tag %s">%s</span>' % (h["change"], "Level up" if h["change"] == "up" else "Level down") if h["change"] else "",
                       esc(_why(by_date.get(h["date"])))) for h in hist)
    return ('<div class="eyebrow">Progress you can trust</div><div class="streak"><div class="streak-n num%s">%d</div><div>'
            '<div style="font-weight:650">%s in a row with real progress</div><div class="tiny sub">%s</div></div></div>'
            '<div class="streak-dots" aria-hidden="true">%s</div><div class="eyebrow" style="margin-top:16px">Level history, your best role</div>'
            '<div class="tiny sub" style="margin-bottom:4px">One row per scored day, newest first, from the dated files in eval/runs.</div>'
            '<div>%s</div>') % ("" if n else " zero", n, "scored day" if n == 1 else "scored days", note, dots, rows)


def render(page):
    """(level card HTML, level-up view HTML) for the static first render."""
    if not page["roles"]:
        return "", ""
    r, nl, qs = compute(page)
    head = ('<div class="lv-head"><div><div class="eyebrow">Next level · Your best role</div><h3>Level %d, %s%s</h3>'
            '<div class="small sub">%s: %s</div></div>%s</div>') % (
        nl["level"], esc(nl["band"]), "" if nl["top"] else ' <span class="arrow">→</span> Level %d, %s' % (nl["next_level"], esc(nl["next_band"])),
        esc(r["on"]), esc(r["title"]),
        "" if nl["top"] else '<div class="lv-need"><b class="num">%s</b><span class="tiny sub">points to go</span></div>' % fp(nl["points_to_next"]))
    quests = ('<div class="quests">%s</div>' % "".join(quest_card(q, nl) for q in qs) if qs
              else '<div class="card small sub">No open actions. The next run adds some from the biggest gaps.</div>')
    view = ('<div class="card lv-card">%s%s%s</div><div class="eyebrow" style="margin:22px 4px 4px">Quests%s</div>'
            '<p class="small" style="margin:0 4px 12px">Your open actions, most points per hour first. Points are fit points on this role: '
            'expected counts each action\'s chance of working, if it works assumes it does. Your plan file is the record, so when one is done, '
            'tell your agent.</p>%s<div class="card" style="margin-top:16px">%s</div>') % (
        head, "" if nl["top"] else _track(nl), verdict(page, nl), "" if nl["top"] else " toward Level %d" % nl["next_level"],
        quests, progress(page))
    return level_card(page, nl), view
