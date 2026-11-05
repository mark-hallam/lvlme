"""The Today screen: the first thing the dashboard shows, in plain words.

Today answers four questions and nothing else above the fold: what level am I, where do I stand in one sentence,
what is the one move for today, and when is the next level expected. Under that: weeks in a row, what is still being
checked, a stepping stone to choose (only when the goal test proposes one), the starting line for the first two
weeks, a level-up or goal-reached moment with its share card, and one tap to Mission control, the full dashboard.

It is rendered once in Python, so it reads without JavaScript; a small script adds the Mission control switch, the
copy buttons and the share image. The words are the ones in docs/LEVELS.md: fit, chance, level, next level. The
flight words (altitude, flight level) stay in Mission control. Everything shown comes from the scored runs, the plan
and the events file; nothing is invented, and a field the engine has not written yet (the fit range) is simply not
shown, with the single fit in its place.
"""
import datetime as dt
import html
import json

import _common as C
import _events as EV
import _goal as G
import _levels as L
import _levels_html as LH
import _weekly as WK

STARTING_LINE_DAYS = 14


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def day_name(iso):
    d = dt.date.fromisoformat(iso)
    return "%s %d %s" % (d.strftime("%A"), d.day, d.strftime("%b"))


def build(page, data, events):
    """Everything Today shows, as plain data (also written to dashboard.json for the person's agents)."""
    run_date, today = page["meta"]["run_date"], data.today
    goal = data.config.get("goal") or {}
    out = {"date": today, "run_date": run_date, "goal": G.goal_line(goal), "goal_by": goal.get("by"),
           "stepping_stone_accepted": goal.get("stepping_stone"), "weeks_in_a_row": WK.weeks_in_a_row(page["progress"], today)}
    out["streak_text"] = WK.streak_text(out["weeks_in_a_row"])
    line = G.starting_line(page, run_date)
    out["start_line"] = line
    if line is None:
        out.update(state="waiting", stand="Your first result is on its way. No role has been judged yet, so there is no level to show.")
        return out
    out["state"] = "ready"
    chance = (line.get("chance_word") or "").lower()
    out["stand"] = "You are at Level %d, %s. Your best match is %s at %s: %s out of 100%s." % (
        line["level"], line["band"], line["role"], line["org"], line["fit_text"],
        ", with a %s chance of an interview" % chance if chance else "")
    rs, acts = L.journey_roles([r for r in page["roles"] if r.get("judged", True)]), page["actions"]
    lead, nl, qs, up = LH.compute(dict(page, roles=rs))
    first = next((q for q in up if not q["a"].get("susp")), up[0] if up else None)   # never lead with a stale posting
    out["move"] = None
    if first:
        a = first["a"]
        out["move"] = {"id": a["id"], "title": a["title"], "why": a.get("why") or "", "effort": a.get("effort") or "",
                       "points": first["exp"], "by": a["date"] if a.get("dated") else None, "done_when": a.get("done_when") or "",
                       "tell": L.tell_agent(a)}
    out["level"], out["band"] = nl["level"], nl["band"]
    out["top"] = nl["top"]
    out["points_to_next"] = None if nl["top"] else nl["points_to_next"]
    out["next_band"] = None if nl["top"] else nl["next_band"]
    out["progress_pct"] = 100.0 if nl["top"] else max(0.0, min(100.0, (nl["fit"] - L.THRESH[nl["level"] - 1]) /
                                                              float(L.THRESH[nl["level"]] - L.THRESH[nl["level"] - 1]) * 100))
    out["goal_check"] = G.check(page, goal, run_date) if goal.get("by") or goal.get("role") else None
    out["checking"] = checking(page, data)
    out["level_up"] = share_of(EV.recent(events, today, "level_up"), page)
    out["goal_reached"] = share_of(EV.recent(events, today, "goal_reached", 60), page)
    out["show_start_line"] = len(page["runs"]) <= 2 or (dt.date.fromisoformat(today) - dt.date.fromisoformat(page["meta"]["baseline"])).days <= STARTING_LINE_DAYS
    out["stone_to_choose"] = stone_to_choose(data, out["goal_check"])
    return out


def share_of(event, page):
    if not event:
        return None
    return dict(event, card=EV.share_card(event, page["meta"]["baseline"]))


def stone_to_choose(data, check):
    """The proposed stepping stone, unless the person has already answered this same proposal or taken a stone."""
    stone = (check or {}).get("stepping_stone")
    if not stone or (data.config.get("goal") or {}).get("stepping_stone"):
        return None
    saved = C.load_json(C.wpath(data.ws, "campaign", "goal-check.json"), None) or {}
    if saved.get("decision") and saved.get("stepping_stone") == stone:
        return None
    return stone


def checking(page, data):
    """What is still being checked, in plain words (empty when nothing is)."""
    roles = page["roles"]
    unjudged = [r for r in roles if not r.get("judged", True)]
    waiting = [r for r in roles if r.get("judged", True) and r.get("awaiting")]
    items = []
    if unjudged:
        items.append("%d of %d open roles %s still being judged. Your level uses the %d judged so far." % (
            len(unjudged), len(roles), "is" if len(unjudged) == 1 else "are", len(roles) - len(unjudged)))
    if waiting:
        items.append("%d %s for the blind review and %s as 2 until it is done." % (
            len(waiting), "score is waiting" if len(waiting) == 1 else "scores are waiting",
            "counts" if len(waiting) == 1 else "count"))
    if len(data.runs) <= 1 and roles:
        items.append("This is your first result. Each later run adds evidence and checks more roles, so it can change.")
    return items


# ---------------------------------------------------------------- html


def render(t, has_numbers_page=False):
    """The Today markup (a string). t is build()'s dict."""
    head = ('<main class="td" id="today" aria-labelledby="tdH" tabindex="-1"><div class="td-wrap">'
            '<div class="td-top"><span class="td-brand">LVLme</span><span class="td-date">%s</span></div>' % esc(day_name(t["date"])))
    goal = '<p class="td-goal">%s</p>' % (esc("Your goal: " + t["goal"]) if t.get("goal") else "")
    if t.get("stepping_stone_accepted"):
        goal += '<p class="td-goal">First step: %s</p>' % esc(t["stepping_stone_accepted"].get("title") or t["stepping_stone_accepted"].get("role", ""))
    if t["state"] == "waiting":
        body = ('<h1 id="tdH" class="td-h">Your first result is on its way</h1><p class="td-stand">%s</p>' % esc(t["stand"]))
        return head + goal + body + _footer(t, has_numbers_page) + "</div></main>"
    parts = [head, goal, _moment(t), _hero(t), '<p class="td-stand">%s</p>' % esc(t["stand"]), _move(t), _next(t),
             _streak(t), _checking(t), _stone(t), _start(t), _reached(t), _footer(t, has_numbers_page), "</div></main>"]
    return "".join(parts)


def _moment(t):
    out = []
    for key, label in (("goal_reached", "Goal reached"), ("level_up", "Level up")):
        e = t.get(key)
        if not e:
            continue
        c = e["card"]
        out.append('<section class="td-moment" aria-label="%s"><div class="td-moment-h">%s</div><div class="td-moment-l">%s</div>'
                   '<button class="td-btn" type="button" data-share data-head="%s" data-line="%s" data-level="%d">Share this</button></section>'
                   % (label, esc(c["head"]), esc(c["line"]), esc(c["head"]), esc(c["line"]), c["level"]))
        break      # one moment at a time: a goal reached beats a level up
    return "".join(out)


def _hero(t):
    to_next = ("You are at the top level." if t["top"] else "%s %s to Level %d, %s" % (
        "%g" % t["points_to_next"], "point" if t["points_to_next"] == 1 else "points", t["level"] + 1, t["next_band"]))
    return ('<div class="td-hero"><div class="td-badge" aria-hidden="true">%d</div><div class="td-hero-t">'
            '<h1 id="tdH" class="td-h">Level %d, %s</h1><div class="td-prog" role="img" aria-label="%s"><span style="width:%g%%"></span></div>'
            '<div class="td-pts">%s</div></div></div>' % (t["level"], t["level"], esc(t["band"]), esc(to_next), t["progress_pct"], esc(to_next)))


def _move(t):
    m = t.get("move")
    if not m:
        return ('<section class="td-card"><div class="td-eyebrow">Your one move today</div>'
                '<p class="td-big">No open move in the plan.</p><p class="td-sub">Ask your agent to add the next move.</p></section>')
    meta = []
    if m["effort"]:
        meta.append(m["effort"])
    if m["points"]:
        meta.append("adds about %s %s" % ("%g" % m["points"], "point" if m["points"] == 1 else "points"))
    if m["by"]:
        meta.append("by " + G.short_date(m["by"]))
    return ('<section class="td-card td-move"><div class="td-eyebrow">Your one move today</div><h2 class="td-big">%s</h2>%s%s%s'
            '<div class="td-actions"><button class="td-btn" type="button" data-copy="%s">Done? Tell your agent</button></div>'
            '<div class="td-msg" role="status"></div></section>') % (
        esc(m["title"]), '<p class="td-sub">%s</p>' % esc(m["why"]) if m["why"] else "",
        '<p class="td-meta">%s</p>' % esc(" · ".join(meta)) if meta else "",
        '<p class="td-sub">Done when: %s</p>' % esc(m["done_when"]) if m["done_when"] else "", esc(m["tell"]))


def _next(t):
    sl = t["start_line"]
    check = t.get("goal_check")
    extra = '<p class="td-sub">%s</p>' % esc(check["text"]) if check and check.get("verdict") not in (None, "unknown") and t.get("goal_by") else ""
    return ('<section class="td-card"><div class="td-eyebrow">Next level</div><p class="td-big">%s</p>%s%s</section>' % (
        esc(sl["next"]), _chance_line(sl), extra))


def _chance_line(sl):
    if sl.get("chance") is None:
        return ""
    return '<p class="td-sub">About a %d%% chance that these moves get you there, counting each move\'s chance of working.</p>' % L.pct(sl["chance"])


def _streak(t):
    n = t["weeks_in_a_row"]
    return ('<section class="td-card td-row"><div class="td-num">%d</div><div><div class="td-eyebrow">Weeks in a row</div>'
            '<p class="td-sub" style="margin:0">%s</p></div></section>' % (n, esc(t["streak_text"])))


def _checking(t):
    if not t.get("checking"):
        return ""
    return ('<section class="td-card"><div class="td-eyebrow">Still being checked</div><ul class="td-list">%s</ul></section>'
            % "".join("<li>%s</li>" % esc(x) for x in t["checking"]))


def _stone(t):
    s = t.get("stone_to_choose")
    if not s:
        return ""
    return ('<section class="td-card"><div class="td-eyebrow">A stepping stone to consider</div><h2 class="td-big">%s</h2>'
            '<p class="td-sub">%s</p><p class="td-sub">You choose. Your goal stays as it is until you do.</p>'
            '<div class="td-actions"><button class="td-btn" type="button" data-copy="%s">Take the stepping stone</button>'
            '<button class="td-btn quiet" type="button" data-copy="%s">Keep my goal</button></div><div class="td-msg" role="status"></div></section>'
            % (esc(s["title"]), esc(s["why"]), esc("Take my stepping stone: run python3 scripts/goal.py stone accept"),
               esc("Keep my goal as it is: run python3 scripts/goal.py stone decline")))


def _start(t):
    if not t.get("show_start_line"):
        return ""
    sl = t["start_line"]
    rng = ("" if sl["has_range"] else '<p class="td-sub">One judging so far. A range shows here once each role has been judged twice.</p>')
    return ('<section class="td-card"><div class="td-eyebrow">Your starting line</div><p class="td-big">Level %d, %s</p>'
            '<p class="td-sub">%s%s for your best match. %s</p>%s</section>' % (
                sl["level"], esc(sl["band"]), esc(sl["fit_text"][:1].upper() + sl["fit_text"][1:]), " out of 100", esc(sl["next"]), rng))


def _reached(t):
    if not t.get("goal_reached"):
        return ""
    return ('<section class="td-card"><div class="td-eyebrow">Next goal</div><p class="td-big">You reached your goal.</p>'
            '<p class="td-sub">Set the next one. The goal you just reached is kept in your history.</p>'
            '<div class="td-actions"><button class="td-btn" type="button" data-copy="%s">Set my next goal</button></div>'
            '<div class="td-msg" role="status"></div></section>' % esc("Set my next goal with LVLme: ask me for the role, the organisations, where and by when, then run scripts/goal.py next-goal."))


def _footer(t, has_numbers_page):
    links = '<a class="td-btn" href="#mission-control" id="toMission">Open Mission control</a>'
    if has_numbers_page:
        links += '<a class="td-btn quiet" href="share-numbers.html">Share my numbers</a>'
    return ('<div class="td-foot"><div class="td-actions">%s</div>'
            '<p class="td-tiny">Mission control is the full dashboard: every role, every number and the what-if switches. '
            'LVLme drafts and measures. You decide and you send.</p></div>'
            '<div class="td-sheet" id="tdSheet" hidden><div class="td-sheet-in" role="dialog" aria-modal="true" aria-label="Share card">'
            '<div class="td-share" id="tdShare"></div><div class="td-actions"><button class="td-btn" type="button" id="tdSave">Save as image</button>'
            '<button class="td-btn quiet" type="button" id="tdClose">Close</button></div>'
            '<p class="td-tiny">Only the level and the dates. No names of organisations or people.</p></div></div>' % links)


# ---------------------------------------------------------------- style and script

HEAD_SCRIPT = ('<script>(function(){var b=document.body;'
               'b.classList.add(location.hash==="#mission-control"?"is-mc":"is-today");})();</script>')

CSS = r"""
/* Today */
.td{--lv:#FF4A1C;--lv-ink:#0C0E12;min-height:100vh;background:var(--bg);color:var(--ink)}
.td-wrap{max-width:600px;margin:0 auto;padding:24px 20px 56px}
.td-top{display:flex;justify-content:space-between;align-items:center;font-size:14px;color:var(--sub)}
.td-brand{font-weight:700;letter-spacing:-.01em;color:var(--ink);font-size:17px}
.td-goal{margin:18px 0 0;font-size:14px;color:var(--sub)}
.td-goal+.td-goal{margin-top:2px}
.td-hero{display:flex;gap:18px;align-items:center;margin:22px 0 6px}
.td-badge{flex:none;width:76px;height:76px;border-radius:50%;background:var(--lv);color:#fff;font-size:44px;font-weight:700;display:flex;align-items:center;justify-content:center;font-variant-numeric:tabular-nums}
.td-hero-t{min-width:0;flex:1}
.td-h{margin:0;font-size:30px;line-height:1.15;letter-spacing:-.02em;font-weight:700}
.td-prog{height:8px;border-radius:99px;background:var(--rule);margin:12px 0 6px;overflow:hidden}
.td-prog span{display:block;height:100%;background:var(--lv);border-radius:99px}
.td-pts{font-size:14px;color:var(--sub)}
.td-stand{font-size:18px;line-height:1.5;margin:14px 0 20px}
.td-card{background:var(--card);border-radius:18px;padding:18px 20px;margin:0 0 14px;box-shadow:var(--shadow)}
.td-eyebrow{font-size:13px;font-weight:600;letter-spacing:.02em;text-transform:uppercase;color:var(--sub);margin-bottom:6px}
.td-big{font-size:20px;line-height:1.35;font-weight:650;margin:0;letter-spacing:-.01em}
.td-sub{font-size:15px;line-height:1.5;color:var(--sub);margin:8px 0 0}
.td-meta{font-size:14px;font-weight:600;margin:10px 0 0;font-variant-numeric:tabular-nums}
.td-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.td-btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 20px;border-radius:999px;border:1px solid var(--lv);background:var(--lv);color:var(--lv-ink);font:inherit;font-size:16px;font-weight:600;text-decoration:none;cursor:pointer}
.td-btn.quiet{background:transparent;border-color:var(--line);color:var(--ink)}
.td-btn:hover{filter:brightness(.96)}
.td-btn:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
.td-msg{font-size:14px;color:var(--sub);margin-top:10px;overflow-wrap:anywhere}
.td-msg:empty{display:none}
.td-row{display:flex;gap:16px;align-items:center}
.td-num{flex:none;font-size:40px;font-weight:700;letter-spacing:-.02em;min-width:44px;text-align:center;font-variant-numeric:tabular-nums}
.td-list{margin:6px 0 0;padding-left:20px;font-size:15px;line-height:1.5;color:var(--sub)}
.td-moment{border-radius:18px;padding:16px 20px;margin:18px 0 0;background:var(--lv);color:var(--lv-ink)}
.td-moment-h{font-size:20px;font-weight:700;letter-spacing:-.01em}
.td-moment-l{font-size:15px;margin-top:4px}
.td-moment .td-btn{background:var(--lv-ink);border-color:var(--lv-ink);color:#fff;margin-top:12px}
.td-foot{margin-top:24px}
.td-tiny{font-size:13px;line-height:1.5;color:var(--sub);margin:14px 0 0}
.td-sheet{position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:flex-end;justify-content:center;z-index:60}
.td-sheet[hidden]{display:none}
.td-sheet-in{background:var(--card);width:100%;max-width:600px;border-radius:22px 22px 0 0;padding:22px 20px 28px;max-height:92vh;overflow:auto}
.td-share{border-radius:18px;padding:22px;background:var(--lv-ink);color:#fff}
.td-share b{display:block;font-size:26px;line-height:1.2;letter-spacing:-.02em}
.td-share span{display:block;margin-top:8px;font-size:15px;color:#d8d8dc}
.td-share i{font-style:normal;font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--lv)}
body.is-today .top,body.is-today .banner,body.is-today .app,body.is-today .bottombar,body.is-today .scrim,body.is-today .modal,body.is-today .tip{display:none!important}
body.is-mc #today{display:none}
.to-today{white-space:nowrap}
@media (max-width:420px){.td-wrap{padding:18px 16px 48px}.td-h{font-size:26px}.td-badge{width:64px;height:64px;font-size:38px}.td-stand{font-size:17px}.td-btn{width:100%}}
"""

JS = r"""
(function(){
"use strict";
var b = document.body;
function showMission(){ return location.hash === "#mission-control"; }
function sync(){
  var mc = showMission();
  b.classList.toggle("is-mc", mc); b.classList.toggle("is-today", !mc);
  window.scrollTo(0, 0);
  if (mc){ window.dispatchEvent(new Event("resize")); } else { var t = document.getElementById("today"); if (t) t.focus({preventScroll: true}); }
}
window.addEventListener("hashchange", sync);
document.querySelectorAll("[data-copy]").forEach(function(btn){
  btn.addEventListener("click", function(){
    var text = btn.getAttribute("data-copy"), msg = btn.closest(".td-card").querySelector(".td-msg");
    function shown(ok){ msg.textContent = ok ? "Copied. Paste it to your agent." : "Copy this to your agent: " + text; }
    if (navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(function(){ shown(true); }, function(){ shown(false); }); }
    else { shown(false); }
  });
});
var sheet = document.getElementById("tdSheet"), shareBox = document.getElementById("tdShare"), cur = null;
function closeSheet(){ if (sheet) sheet.hidden = true; }
document.querySelectorAll("[data-share]").forEach(function(btn){
  btn.addEventListener("click", function(){
    cur = {head: btn.getAttribute("data-head"), line: btn.getAttribute("data-line")};
    shareBox.textContent = "";
    [["i", "LVLme"], ["b", cur.head], ["span", cur.line]].forEach(function(p){ var e = document.createElement(p[0]); e.textContent = p[1]; shareBox.appendChild(e); });
    sheet.hidden = false;
  });
});
if (sheet){
  document.getElementById("tdClose").addEventListener("click", closeSheet);
  sheet.addEventListener("click", function(e){ if (e.target === sheet) closeSheet(); });
  document.addEventListener("keydown", function(e){ if (e.key === "Escape") closeSheet(); });
  document.getElementById("tdSave").addEventListener("click", function(){
    var cv = document.createElement("canvas"); cv.width = 1200; cv.height = 630; var x = cv.getContext("2d"), F = "-apple-system,Helvetica,Arial";
    x.fillStyle = "#0C0E12"; x.fillRect(0, 0, 1200, 630);
    x.fillStyle = "#FF4A1C"; x.font = "650 26px " + F; x.fillText("LVLME", 70, 100);
    x.fillStyle = "#ffffff"; var hs = 64; do { x.font = "700 " + hs + "px " + F; } while (x.measureText(cur.head).width > 1060 && --hs > 30); x.fillText(cur.head, 70, 300);
    x.fillStyle = "#d8d8dc"; x.font = "400 30px " + F; x.fillText(cur.line, 70, 360);
    x.fillStyle = "#9a9aa0"; x.font = "400 22px " + F; x.fillText("Measured by evidence. Only the level and the dates are shown.", 70, 560);
    var a = document.createElement("a"); a.download = "lvlme-level.png"; a.href = cv.toDataURL("image/png"); a.click();
  });
}
})();
"""
