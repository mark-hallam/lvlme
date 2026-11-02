"""The level-up view and the hero's level card, rendered once in Python for the static page.

The page script renders the same markup again on load (so the what-if switches
and the organisation selector can change it); this first render means the next
level, the quests and the level history are readable even with JavaScript off.
It follows the best role overall with every open action switched on, which is
also what the agent briefing reports. The next level and the quest points are
measured on the best fit across every role, so a role other than today's best
can carry the level; it is named wherever it does. Keep the markup in step with JS_LEVELS in
_dashboard_assets.py.

One yardstick: Do next and the quests are one ranked list (_levels.up_next: the
actions on the path to the next level first, then the most points per hour), and
every action shows one points number wherever it appears, its expected points
toward the next level. Internal ids (A04, E02) stay in the drill-in detail.
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


def cap1(s):
    return s[:1].upper() + s[1:] if s else ""


def status_name(st):
    return STATUS.get(st, "To do")


def compute(page):
    """The next level, the quests and their Do next order, on the best fit across every role, every open action on."""
    rs, acts, today = L.journey_roles(page["roles"]), page["actions"], page["meta"]["run_date"]
    nl = L.next_level(rs, acts, page["caps"], page["weights"], today)
    qs = L.quests(rs, acts, page["caps"], page["weights"], nl)
    return rs[0], nl, qs, L.up_next(qs, nl)


def role_name(r):
    """A role named in a sentence: its title in bold, then its organisation."""
    return "<b>%s</b> (%s)" % (esc(r["title"]), esc(r["on"]))


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
    rows = "".join('<div class="lv-step" tabindex="0" data-act="%s"><span class="lv-step-t">%s</span>'
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


def verdict(page, nl, lead):
    if nl["top"]:
        return ('<div class="lv-verdict"><div class="lv-v-h">Top level</div><p class="small">Strong is the highest band. '
                'The work now is keeping the evidence fresh and the warm paths warm.</p></div>')
    lvl = "Level %d (%s)" % (nl["next_level"], esc(nl["next_band"]))
    if nl["reachable"]:
        s = nl["set"]
        n = len(s["acts"])
        if s["role"] is lead:
            how = ", at a fit of %s counting each action's chance of working." % fp(s["fit"])
        else:
            how = (" by lifting your fit for %s from %s to %s, counting each action's chance of working. That role would then be "
                   "your best." % (role_name(s["role"]), fp(s["role"]["fit"]), fp(s["fit"])))
        out = ['<div class="lv-verdict"><div class="lv-v-h">%s can get you there</div>' % ("One action" if n == 1 else "%d actions" % n),
               '<p class="small">If %s, you\'re expected to reach %s on <b>%s</b>%s</p>' % (
                   "it lands on its target date" if n == 1 else "they land on their target dates", lvl, long_date(s["date"]), how),
               _chance(s, "Chance it really happens: ")]
        if nl["plan"]["date"] and nl["plan"]["date"] < s["date"]:
            out.append('<p class="small sub">Doing everything switched on in the plan is expected to get there sooner, on %s.</p>'
                       % long_date(nl["plan"]["date"]))
        if not s["exact"]:
            out.append('<p class="small sub">The plan is long, so this set comes from a quick search; a smaller one may exist.</p>')
        return "".join(out) + _steps(s["acts"]) + "</div>"
    m, bc = nl["missing"], nl.get("best_case")
    same = m["role"] is lead
    out = ['<div class="lv-verdict"><div class="lv-v-h">Not reachable on the current plan</div>',
           '<p class="small">Counting each action\'s chance of working, no set of your switched-on actions reaches %s. All of them together '
           'are expected to take %s to %s, which is <b>%s points short</b>.</p>' % (
               lvl, "this role" if same else "your best fit, on %s," % role_name(m["role"]), fp(nl["plan"]["fit_expected"]), fp(m["points"]))]
    if bc:
        k = len(bc["acts"])
        reach = ("reach%s %s" % ("es" if k == 1 else "", fp(bc["fit"])) if bc["role"] is lead
                 else "lift%s %s from %s to %s" % ("s" if k == 1 else "", role_name(bc["role"]), fp(bc["role"]["fit"]), fp(bc["fit"])))
        out.append('<p class="small"><b>Best case only:</b> %s %s by %s, but only if %s.</p>' % (
            "the action below" if k == 1 else "the %d actions below together" % k, reach, long_date(bc["date"]),
            "it works" if k == 1 else "both work" if k == 2 else "all of them work"))
        out.append(_chance(bc, "Chance of that: ") + _steps(bc["acts"]))
    else:
        out.append('<p class="small sub">Not even the best case gets there: if every action works, your best fit reaches %s.</p>'
                   % fp(nl["plan"]["fit_best"]))
    out.append('<div class="eyebrow" style="margin-top:16px">What is missing</div>')
    who = "this role" if same else role_name(m["role"])
    if m["ceiling"] < nl["target"]:
        out.append('<p class="small">Even with every factor at the most the plan\'s caps allow, %s tops out at %s. Reaching %s needs '
                   'something the caps rule out within this plan, such as more years in a similar role, or a different role.</p>'
                   % (who, fp(m["ceiling"]), lvl))
    else:
        out.append('<p class="small sub">Room left on %s within the plan\'s caps, in fit points, if new actions fully work. The %s '
                   'points have to come from here: add an action where none exists, or raise the odds of the ones you have.</p>' % (
                       who if same else who + ", the role the plan takes closest,", fp(m["points"])))
    rows = "".join('<div class="lv-room"><span><b style="font-weight:600">%s</b><div class="tiny sub">%s</div></span><b class="num">+%s</b></div>' % (
        esc(page["dimNames"][x["dimension"]]), "Open actions cover part of it" if x["covered"] else "No open action raises it for this role",
        fp(x["points"])) for x in m["room"])
    out.append("<div>%s</div></div>" % (rows or '<div class="small sub">No room left within the caps.</div>'))
    return "".join(out)


def no_points(q, nl):
    """What a quest card says when the action alone adds nothing to the best fit."""
    toward = "to your best fit" if nl["top"] else "toward Level %d" % nl["next_level"]
    if q["crit"] or (q["bc"] and not nl.get("reachable")):
        return "No points %s on its own; it counts together with the others in the set" % toward
    return "No points %s on its own" % toward


def via(q, lead):
    """The second line of a quest card when the action carries the level through a role other than today's best.
    The fits are the role's, not more points for the action: what it adds to today's best role is in the action pane."""
    if q["role"] is lead or q["exp"] <= 0:
        return ""
    return ('<div class="tiny sub q-via">Lifts %s from %s to %s, which would then be your best role.</div>' % (
        role_name(q["role"]), fp(q["role"]["fit"]), fp(q["fit_after"])))


def path_tag(q, nl):
    """The tag an action on the path to the next level carries in Do next and on its quest card, or None."""
    if q["crit"]:
        return "On the path to Level %d" % nl["next_level"]
    if q["bc"] and not nl.get("reachable"):
        return "Needed for the best case"
    return None


def points(q):
    """The one points number an action shows everywhere outside the What if rail: its expected points
    toward the next level, on its own, counting its chance. None when it changes no score."""
    return "+" + fp(max(0.0, q["exp"])) if q["a"]["effects"] else None


def do_next_rows(nl, ordered, limit=None):
    """The Do next rows: status (a word beside the dot), title, owner and date, and the one points number."""
    if not ordered:
        return '<div class="small sub">No open actions. The next run adds some from the biggest gaps.</div>'
    rows = []
    for q in ordered[:limit] if limit else ordered:
        a, tag = q["a"], path_tag(q, nl)
        rows.append('<div class="dn" tabindex="0" data-act="%s"><span class="status-dot %s"></span><div style="flex:1;min-width:0">'
                    '<div class="dn-t">%s</div><div class="tiny sub">%s%s · %s · %s%s</div></div><div class="dn-p">%s</div></div>' % (
                        esc(a["id"]), esc(a["status"]), esc(a["title"]), status_name(a["status"]),
                        "" if q["on"] else ", switched off", esc(a["owner"]), "by " + short(a["date"]) if a.get("dated") else "no target date yet",
                        ' · <span class="dn-tag">%s</span>' % tag if tag else "", points(q) or "credibility"))
    return "".join(rows)


def quest_card(q, nl, lead):
    a = q["a"]
    tag = path_tag(q, nl)
    tags = "".join([
        '<span class="tag%s">%s</span>' % (" crit" if q["crit"] else "", tag) if tag else "",
        '<span class="tag">Estimated effect</span>' if a.get("derived") else "",
        '<span class="tag pend">No movement in %d runs</span>' % a["stale"] if a.get("stale") else ""])
    if not a["effects"]:
        pts = '<span class="small sub">Protects credibility, no score change</span>'
    elif q["exp"] <= 0 and q["works"] <= 0:
        pts = '<span class="small sub">%s</span>' % no_points(q, nl)
    else:
        pts = '<span><b class="num">%s</b> <span class="tiny sub">expected</span></span>' % points(q)
    return ('<div class="quest%s"><div class="q-top"><div class="q-tags">%s</div><span class="q-id"><span class="status-dot %s"></span>%s</span></div>'
            '<div class="q-title">%s</div><div class="q-pts">%s</div>%s<div class="q-meta">%s%s · %s · %d%% chance</div>'
            '<div class="small"><span class="sub">Done when:</span> %s</div>'
            '<div class="q-foot small"><span><span class="sub">Done? Tell your agent:</span><span class="q-text">%s</span></span></div></div>') % (
        " crit" if q["crit"] else "", tags, esc(a["status"]), status_name(a["status"]), esc(a["title"]), pts, via(q, lead), esc(a["owner"]),
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
             "newly checked evidence (%s)" % plural(len(d["evidence"]), "item") if d["evidence"] else "",
             "%s done with evidence" % plural(len(d["actions"]), "action") if d["actions"] else ""]
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
    return ('<h2 class="eyebrow">Progress you can trust</h2><div class="streak"><div class="streak-n num%s">%d</div><div>'
            '<div style="font-weight:650">%s in a row with real progress</div><div class="tiny sub">%s</div></div></div>'
            '<div class="streak-dots" aria-hidden="true">%s</div><h3 class="eyebrow" style="margin-top:16px">Level history, your best role</h3>'
            '<div class="tiny sub" style="margin-bottom:4px">One row per scored day, newest first, from the dated files in eval/runs.</div>'
            '<div>%s</div>') % ("" if n else " zero", n, "scored day" if n == 1 else "scored days", note, dots, rows)


def quests_intro(nl):
    """How the quests are ordered and their points counted, in plain words."""
    if nl["top"]:
        return ("Your open actions, in the same order as Do next, most points per hour first. Points are what each action on its own "
                "adds to your best fit, counting its chance of working.")
    return ("Your open actions, in the same order as Do next: the ones on the path to Level %d first, then the most points per hour. "
            "Points are what each action on its own adds to your best fit toward Level %d, counting its chance of working. Actions "
            "that raise the same factor overlap, so their points don't simply add up; the panel above shows what they do together."
            % (nl["next_level"], nl["next_level"]))


def render(page):
    """(level card HTML, level-up view HTML) for the static first render."""
    if not page["roles"]:
        return "", ""
    r, nl, _, qs = compute(page)
    head = ('<div class="lv-head"><div><h2 class="eyebrow">Next level · Your best role</h2><h3>Level %d, %s%s</h3>'
            '<div class="small sub">%s: %s</div></div>%s</div>') % (
        nl["level"], esc(nl["band"]), "" if nl["top"] else ' <span class="arrow">→</span> Level %d, %s' % (nl["next_level"], esc(nl["next_band"])),
        esc(r["on"]), esc(r["title"]),
        "" if nl["top"] else '<div class="lv-need"><b class="num">%s</b><span class="tiny sub">points to go</span></div>' % fp(nl["points_to_next"]))
    quests = ('<div class="quests">%s</div>' % "".join(quest_card(q, nl, r) for q in qs) if qs
              else '<div class="card small sub">No open actions. The next run adds some from the biggest gaps.</div>')
    view = ('<div class="card lv-card">%s%s%s</div><h2 class="eyebrow" style="margin:22px 4px 4px">Quests%s</h2>'
            '<p class="small" style="margin:0 4px 12px">%s Your plan file is the record, so when one is done, tell your agent.</p>'
            '%s<div class="card" style="margin-top:16px">%s</div>') % (
        head, "" if nl["top"] else _track(nl), verdict(page, nl, r), "" if nl["top"] else " toward Level %d" % nl["next_level"],
        quests_intro(nl), quests, progress(page))
    return level_card(page, nl), view
