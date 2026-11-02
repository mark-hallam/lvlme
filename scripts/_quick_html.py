"""The LVLme quick result page (index.html in a quick folder): one self-contained page.

Rendered once in Python from result.json. Inline CSS, no script, no external
requests (no fonts, images or styles loaded from anywhere). Light by default,
with a dark mode that follows the device. Plain semantic HTML: headings,
lists and one table, so a screen reader or a text browser reads it in order.
The colours are the dashboard's tokens, so the two pages look like one product.
"""
import html

BANDS = ["Very low", "Low", "Moderate", "Good", "Strong"]
LEVELS = {"verified": ("Verified", "v"), "corroborated": ("Corroborated", "v"),
          "partially_verified": ("Partly checked", "p"), "self_reported": ("Self-reported", "s"),
          "unverified": ("No source", "c"), "contradicted": ("Contradicted", "c")}
SOURCES = {"resume": "CV", "interview": "your answer", "linkedin_export": "LinkedIn export",
           "linkedin_profile": "LinkedIn text you pasted", "github": "GitHub", "website": "website",
           "app_store": "app store", "publication": "publication", "certification": "certificate",
           "talk": "talk", "web_search": "web search", "email": "email", "reference": "referee",
           "document": "document", "other": "other"}
EXPLAIN = {
    "Very low": "As things stand, this application would most likely be screened out.",
    "Low": "An interview is possible, but unlikely as things stand.",
    "Moderate": "You are in the running for an interview, but not yet a strong pick.",
    "Good": "You look like a typical shortlisted applicant for this role.",
    "Strong": "You stand out against most shortlisted applicants for this role.",
}
REVIEW = {"agreed": ("Reviewer agreed", "v"), "disputed": ("Reviewers disagreed", "p"),
          "awaiting": ("Waiting for the reviewer", "p"), "not_needed": ("2 or under: no review needed", "s")}

CSS = """
:root{color-scheme:light;--bg:#f2f2f5;--card:#fff;--card2:#f6f6f8;--ink:#1d1d1f;--sub:#56565b;--rule:#e2e2e7;
--accent:#084c9e;--on-accent:#fff;--accent-soft:#e7f0fb;--warn:#843800;--warn-bg:#fff4d6;
--shadow:0 1px 2px rgba(0,0,0,.04),0 8px 24px rgba(0,0,0,.06);--pip:#d9d9de;
--v-bg:#dff3e4;--v-t:#14501f;--c-bg:#fde3e1;--c-t:#7a1810;--p-bg:#fcefd6;--p-t:#6b3f00;--s-bg:#ececf0;--s-t:#3a3a3c}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#111113;--card:#1c1c1e;--card2:#26262a;--ink:#f5f5f7;
--sub:#b8b8be;--rule:#38383c;--accent:#64b0ff;--on-accent:#0b1a2b;--accent-soft:#172c45;--warn:#ffb340;--warn-bg:#3a2e0b;
--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.4);--pip:#48484c;
--v-bg:#1e3a24;--v-t:#a6efb0;--c-bg:#3d1714;--c-t:#ffc2ba;--p-bg:#3a2a10;--p-t:#ffd99a;--s-bg:#2c2c30;--s-t:#d8d8dc}}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink)}
body{font:16px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;
-webkit-font-smoothing:antialiased;overflow-wrap:break-word}
a{color:var(--accent)}
.wrap{max-width:780px;margin:0 auto;padding:20px 16px 48px}
.top{display:flex;align-items:center;gap:10px;margin:4px 2px 16px}
.mark{width:28px;height:28px;border-radius:8px;background:var(--accent);display:grid;place-items:center}
.mark svg{width:16px;height:16px}
.top b{font-size:17px;letter-spacing:-.01em;white-space:nowrap}
.top .sub{margin-left:auto;font-size:13px;text-align:right}
.sub{color:var(--sub)}.small{font-size:14px}.tiny{font-size:13px}.num{font-variant-numeric:tabular-nums}
.card{background:var(--card);border-radius:18px;box-shadow:var(--shadow);padding:20px 22px}
.card+.card,section+section{margin-top:16px}
.eyebrow{font-size:13px;font-weight:650;color:var(--sub);letter-spacing:.03em;text-transform:uppercase;margin:0 0 6px}
h1{font-size:28px;line-height:1.15;letter-spacing:-.02em;margin:0 0 6px}
h2{font-size:20px;letter-spacing:-.015em;margin:0 0 4px}
h3{font-size:16px;margin:0}
p{margin:6px 0}
.odds{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:18px 0 12px}
.tile{background:var(--card2);border-radius:14px;padding:14px 16px}
.tile .k{font-size:13px;color:var(--sub);font-weight:600}
.tile .b{font-size:24px;font-weight:700;letter-spacing:-.015em;margin:2px 0 8px}
.meter{display:grid;grid-template-columns:repeat(5,1fr);gap:4px}
.meter i{height:6px;border-radius:3px;background:var(--pip)}
.meter i.on{background:var(--accent)}
.meter-l{display:flex;justify-content:space-between;font-size:11px;color:var(--sub);margin-top:4px}
.lead{font-size:17px}
.fit{margin:14px 0 4px}
.fit-h{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;font-size:14px}
.fit-h .k{color:var(--sub);font-weight:600}
.track{display:flex;height:10px;border-radius:5px;background:var(--pip);overflow:hidden;margin:6px 0}
.track .now{background:var(--accent)}
.track .maybe{background:repeating-linear-gradient(135deg,var(--accent) 0 2px,var(--accent-soft) 2px 5px)}
.note{background:var(--card2);border-radius:12px;padding:10px 14px;margin-top:10px;font-size:14px}
.score.nc{color:var(--sub);font-weight:600}
.banner{background:var(--warn-bg);color:var(--warn);border-radius:12px;padding:10px 14px;font-size:14px;font-weight:550;margin-top:12px}
ul.rows{list-style:none;margin:10px 0 0;padding:0}
ul.rows>li{border-top:1px solid var(--rule);padding:14px 0}
ul.rows>li:first-child{border-top:none;padding-top:6px}
.row-h{display:flex;align-items:baseline;gap:10px}
.row-h h3{flex:1}
.pips{display:inline-flex;gap:3px;vertical-align:middle}
.pips i{width:9px;height:9px;border-radius:50%;background:var(--pip)}
.pips i.on{background:var(--accent)}
.score{font-weight:650;white-space:nowrap}
.chip{display:inline-block;font-size:12px;font-weight:600;border-radius:999px;padding:2px 9px;white-space:nowrap}
.chip.v{background:var(--v-bg);color:var(--v-t)}.chip.c{background:var(--c-bg);color:var(--c-t)}
.chip.p{background:var(--p-bg);color:var(--p-t)}.chip.s{background:var(--s-bg);color:var(--s-t)}
.ev{list-style:none;margin:8px 0 0;padding:0}
.ev li{display:flex;gap:8px;align-items:flex-start;font-size:14px;margin-top:6px}
.ev .id{color:var(--sub);font-size:12px;font-weight:600;min-width:28px;padding-top:2px}
.ev .chip{margin-top:1px}
.why{font-size:13px;color:var(--warn);margin-top:6px}
ol.fixes{list-style:none;margin:10px 0 0;padding:0;counter-reset:f}
ol.fixes li{counter-increment:f;display:grid;grid-template-columns:34px 1fr;gap:4px 12px;border-top:1px solid var(--rule);padding:14px 0}
ol.fixes li:first-child{border-top:none;padding-top:6px}
ol.fixes li::before{content:counter(f);grid-row:span 3;width:30px;height:30px;border-radius:50%;background:var(--accent-soft);
color:var(--accent);font-weight:700;display:grid;place-items:center}
.gain{font-weight:700;color:var(--accent)}
.step{font-size:15px}
.step b{font-weight:650}
.all{background:var(--accent-soft);border-radius:14px;padding:12px 16px;margin-top:6px;font-size:15px}
table{border-collapse:collapse;width:100%;font-size:14px;margin-top:8px}
th,td{text-align:left;padding:7px 8px;border-top:1px solid var(--rule);vertical-align:top}
th{font-weight:600;color:var(--sub)}
.deeper{display:flex;gap:16px;align-items:center}
.deeper .say{background:var(--accent);color:var(--on-accent);border-radius:12px;padding:10px 14px;font-weight:650;white-space:nowrap}
footer{margin-top:20px;font-size:13px;color:var(--sub);padding:0 4px}
@media (max-width:560px){h1{font-size:24px}.tile{padding:12px}.tile .b{font-size:21px}
.deeper{flex-direction:column;align-items:flex-start}.card{padding:18px 16px}}
@media (max-width:340px){.odds{grid-template-columns:1fr}}
"""

LOGO = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 13 L6 7 L9 10 L14 3" fill="none" stroke="#fff" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def num(v):
    v = round(float(v), 1)
    return "%d" % v if v == int(v) else "%.1f" % v


def headline(r, start=True):
    """'Low chance of an interview, very low chance of an offer' from a result (or any bands dict).

    start=False gives the lower-case form for the middle of a sentence."""
    text = "%s chance of an interview, %s chance of an offer" % (r["interview_band"], r["offer_band"].lower())
    return text if start else text[0].lower() + text[1:]


def and_list(names):
    return names[0] if len(names) == 1 else "%s and %s" % (", ".join(names[:-1]), names[-1])


def unchecked_names(result):
    """'public signal and application readiness': the factors LVLme quick cannot check, in a sentence."""
    return and_list([x["name"].lower() for x in result.get("not_checked") or []])


def top_of_range(result):
    """The fit if the unchecked factors turned out strong, or None when they could add nothing."""
    top = result.get("if_unchecked_strong")
    return top if top and top.get("gain", 0) > 0 else None


def fit_sentence(result):
    """'Fit 41 of 100 today, up to 56 if public signal and application readiness (not checked here) turn out
    strong.' The range is honest about what one posting and a CV cannot show."""
    top = top_of_range(result)
    if not top:
        return "Fit %s of 100." % num(result["fit"])
    return "Fit %s of 100 today, up to %s if %s (not checked here) turn out strong." % (
        num(result["fit"]), num(top["fit"]), unchecked_names(result))


def long_date(iso):
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]
    y, m, d = iso.split("-")
    return "%d %s %s" % (int(d), months[int(m) - 1], y)


def meter(band, label):
    i = BANDS.index(band)
    pips = "".join('<i class="on"></i>' if k <= i else "<i></i>" for k in range(5))
    return ('<div class="tile"><div class="k">%s</div><div class="b">%s</div>'
            '<div class="meter" role="img" aria-label="%s: %s, step %d of 5">%s</div>'
            '<div class="meter-l" aria-hidden="true"><span>Very low</span><span>Strong</span></div></div>'
            % (label, esc(band), label, esc(band), i + 1, pips))


def pips(score):
    return '<span class="pips" aria-hidden="true">%s</span>' % "".join(
        '<i class="on"></i>' if k < score else "<i></i>" for k in range(5))


def chip(text, cls):
    return '<span class="chip %s">%s</span>' % (cls, esc(text))


def adjustments(result):
    out = []
    for a in result["adjustments"]:
        if a.startswith("Warm referral"):
            out.append("Someone inside has agreed to refer you, so the interview chance moves up one step.")
        elif a.startswith("Hard requirement lacking"):
            note = result.get("hard_requirement_note")
            out.append("A hard requirement is missing%s, so both chances move down one step." % (
                " (%s)" % note if note else ""))
        elif a.startswith("Cold application only"):
            out.append("Nobody inside has vouched for you yet, so the offer chance is capped at Low.")
        elif a.startswith("Eligibility blocker"):
            out.append("The posting has an eligibility rule you have not cleared, so eligibility counts 0.")
    return out


def hero(result):
    r = result["role"]
    locs = ", ".join(r["locations"])
    remote = "Remote" if r.get("remote") is True and "remote" not in locs.lower() else ""
    where = " · ".join(x for x in [esc(r["org_name"]), esc(locs), remote] if x)
    link = (' · <a href="%s">Open the posting</a>' % esc(r["url"])) if str(r.get("url") or "").startswith(
        ("http://", "https://")) else ""
    banners = "".join('<div class="banner">%s</div>' % esc(a) for a in adjustments(result))
    return ('<section class="card" aria-labelledby="oddsH"><p class="eyebrow">Your honest odds today</p>'
            '<h1>%s</h1><p class="sub small">%s%s</p>'
            '<div class="odds">%s%s</div>'
            '<p class="lead" id="oddsH"><b>%s.</b> %s</p>%s'
            '<p class="sub small">The chances are for today\'s fit. They are judgement estimates, not statistics. '
            'Most applicants to competitive roles are turned down, so LVLme starts from "unlikely" and only evidence '
            'moves it.</p>%s</section>'
            % (esc(r["title"]), where, link, meter(result["interview_band"], "Interview chance"),
               meter(result["offer_band"], "Offer chance"), esc(headline(result)),
               esc(EXPLAIN[result["interview_band"]]), fit_range(result), banners))


def fit_range(result):
    """Today's fit as a bar, with the part the unchecked factors could add striped, and the words for it."""
    top = top_of_range(result)
    now = '<i class="now" style="width:%s%%"></i>' % num(result["fit"])
    if not top:
        return ('<div class="fit"><div class="fit-h"><span class="k">Fit, out of 100</span><span><b class="num">%s'
                '</b></span></div><div class="track" aria-hidden="true">%s</div></div>' % (num(result["fit"]), now))
    many = len(result["not_checked"]) > 1
    return ('<div class="fit"><div class="fit-h"><span class="k">Fit, out of 100</span><span><b class="num">%s</b> '
            'today, up to <b class="num">%s</b></span></div>'
            '<div class="track" aria-hidden="true">%s<i class="maybe" style="width:%s%%"></i></div>'
            '<p class="tiny sub">The striped part is %s. LVLme quick cannot check %s from one posting and a CV, '
            'so today %s 0.</p></div>' % (
                num(result["fit"]), num(top["fit"]), now, num(top["gain"]), esc(unchecked_names(result)),
                "them" if many else "it", "they count" if many else "it counts"))


def evidence_list(rows):
    if not rows:
        return '<p class="small sub">No evidence cited, so this counts 0.</p>'
    items = []
    for e in rows:
        label, cls = LEVELS.get(e["level"], (e["level"], "s"))
        src = ", ".join(SOURCES.get(s, s) for s in e["sources"])
        items.append('<li><span class="id">%s</span><span>%s %s%s</span></li>' % (
            esc(e["id"]), chip(label, cls), esc(e["claim"]), (' <span class="sub">(%s)</span>' % esc(src)) if src else ""))
    return '<ul class="ev">%s</ul>' % "".join(items)


def factors(result):
    rows = []
    for f in result["factors"]:
        label, cls = REVIEW[f["review"]["status"]]
        if f["review"]["status"] == "disputed":
            label = "Reviewers disagreed (%d and %d)" % (f["review"]["judge_score"], f["review"]["reviewer_score"])
        why = "".join('<p class="why">%s</p>' % esc(w) for w in f["why_counted"])
        rows.append('<li><div class="row-h"><h3>%s</h3><span class="score num">%s %d of 5</span></div>'
                    '<p class="tiny sub">%s of %s fit points · %s</p>%s%s%s</li>' % (
                        esc(f["name"]), pips(f["score"]), f["score"], num(f["points"]), num(f["max_points"]),
                        chip(label, cls), ('<p class="small">%s</p>' % esc(f["note"])) if f["note"] else "",
                        evidence_list(f["evidence"]), why))
    for x in result["not_checked"]:
        rows.append('<li><div class="row-h"><h3>%s</h3><span class="score nc">Not checked</span></div>'
                    '<p class="tiny sub">Up to %s fit points · %s</p><p class="small">%s</p></li>' % (
                        esc(x["name"]), num(x["max_points"]), chip("Counts 0 today", "s"), esc(x.get("what", ""))))
    note = unchecked_note(result)
    return ('<section class="card" aria-labelledby="whyH"><p class="eyebrow">Why</p><h2 id="whyH">Factor by factor</h2>'
            '<p class="small sub">Every point cites evidence, and a score can be no higher than its best evidence '
            'supports. A line on a CV alone is self-reported.</p><ul class="rows">%s</ul>%s</section>' % (
                "".join(rows), note))


def unchecked_note(result):
    """The top of the range, in words, under the factors: what the fit would be if the unchecked ones were strong."""
    top = top_of_range(result)
    if not top:
        return ""
    names = unchecked_names(result)
    many = len(result["not_checked"]) > 1
    return ('<p class="note">%s %s not checked here. If %s strong (5 of 5), the fit is <b class="num">%s</b> '
            'instead of %s: %s. The full campaign checks %s.</p>' % (
                esc(names[0].upper() + names[1:]), "are" if many else "is",
                "both turn out" if len(result["not_checked"]) == 2 else "they turn out" if many else "it turns out",
                num(top["fit"]), num(result["fit"]), esc(headline(top, start=False)), "them" if many else "it"))


def band_change(result, f):
    """How a fix moves the two chances, in words."""
    moves = []
    for key, after, label in (("interview_band", "interview_after", "interview"), ("offer_band", "offer_after", "offer")):
        if f[after] != result[key]:
            moves.append("%s chance %s to %s" % (label, result[key], f[after]))
    return ", ".join(moves) if moves else "chances stay in the same bands"


def fixes(result):
    if not result["fixes"]:
        return ('<section class="card"><p class="eyebrow">What would raise your odds</p><h2>No fix found</h2>'
                '<p class="small sub">None of the fixes considered adds fit points. Say "run LVLme" for the full '
                'campaign, which looks wider.</p></section>')
    items = []
    for f in result["fixes"]:
        items.append('<li><h3>%s</h3><p class="small"><span class="gain">+%s fit points</span> · %s %d to %d · '
                     '%s</p><p class="step"><b>Next step:</b> %s</p></li>' % (
                         esc(f["title"]), num(f["gain"]), esc(f["name"]), f["from"], f["to"],
                         esc(band_change(result, f)), esc(f["next_step"])))
    c = result["if_all_fixes"]
    n = len(result["fixes"])
    all_line = ('<div class="all">If %s land: fit <b class="num">%s</b> (up %s), %s.</div>' % (
        "all %s" % ("three" if n == 3 else "two") if n > 1 else "it", num(c["fit"]), num(c["gain"]),
        esc(headline(c, start=False))))
    return ('<section class="card" aria-labelledby="fixH"><p class="eyebrow">What would raise your odds</p>'
            '<h2 id="fixH">The top %s</h2><p class="small sub">Ranked by the fit points each adds, with the same '
            'maths as the score. Each one is capped at what can realistically change in a few months.</p>'
            '<ol class="fixes">%s</ol>%s</section>' % ("fix" if n == 1 else "%d fixes" % n, "".join(items), all_line))


def brief(result):
    b = result["brief"]
    lead = "".join("<li><span>%s %s <span class=\"sub\">(%s)</span></span></li>" % (
        chip(LEVELS[e["level"]][0], LEVELS[e["level"]][1]), esc(e["claim"]), esc(e["factor"])) for e in b["lead_with"])
    back = "".join("<li><span>%s %s</span></li>" % (chip(LEVELS[e["level"]][0], LEVELS[e["level"]][1]), esc(e["claim"]))
                   for e in b["back_up"])
    parts = []
    if lead:
        parts.append('<h3>Lead with</h3><ul class="ev">%s</ul>' % lead)
    if back:
        parts.append('<h3 style="margin-top:12px">Have a source ready for</h3><ul class="ev">%s</ul>' % back)
    return ('<section class="card" aria-labelledby="briefH"><p class="eyebrow">Your brief</p>'
            '<h2 id="briefH">Before you apply</h2>%s<p class="small sub" style="margin-top:12px">LVLme gives fixes and a '
            'brief, never application answers: you write those in your own words. Some employers publish guidance on '
            'how candidates may use AI; check theirs.</p></section>' % "".join(parts))


def checked(result):
    rv = result["review"]
    rows = []
    for d in rv["disputes"]:
        rows.append("<tr><td>%s</td><td class=\"num\">%d</td><td class=\"num\">%d</td><td class=\"num\">%d</td></tr>" % (
            esc(next(f["name"] for f in result["factors"] if f["dimension"] == d["dimension"])),
            d["scorer"]["score"], d["reviewer"]["score"], d["stands"]))
    table = ('<table><thead><tr><th scope="col">Factor</th><th scope="col">First judge</th>'
             '<th scope="col">Blind reviewer</th><th scope="col">Counts as</th></tr></thead><tbody>%s</tbody></table>'
             '<p class="tiny sub">A disagreement counts as 2 until a third reviewer settles it. The full campaign '
             'runs that tie-break.</p>' % "".join(rows)) if rows else ""
    flags = "".join("<li><span>%s: \"%s\" %s</span></li>" % (
        "Hard requirement missing" if f["flag"] == "hard_requirement_lacking" else "Eligibility blocked",
        esc(f["posting_sentence"]), {"applied": chip("Applied", "c"), "dismissed": chip("Dismissed: " + f["dismissed"], "s"),
                                     "not_in_posting": chip("Not in the posting, ignored", "s")}[f["status"]])
        for f in rv["flags"])
    agreed = len(rv["agreed"])
    need = agreed + len(rv["disputes"]) + sum(1 for f in result["factors"] if f["review"]["status"] == "awaiting")
    lead = ("No score was above 2, so no review was needed." if need == 0 else
            "A second agent, given only the rubric, your evidence and the posting, scored every factor above 2 "
            "without seeing the first scores. It agreed on %d of %d." % (agreed, need))
    return ('<section class="card" aria-labelledby="chkH"><p class="eyebrow">How this was checked</p>'
            '<h2 id="chkH">A blind second opinion</h2><p class="small">%s</p>%s%s</section>' % (
                esc(lead), table, ('<ul class="ev">%s</ul>' % flags) if flags else ""))


def deeper():
    return ('<section class="card" aria-labelledby="deepH"><div class="deeper"><div><p class="eyebrow">Go deeper</p>'
            '<h2 id="deepH">Want the whole climb?</h2><p class="small sub">The full campaign checks every open role at '
            'the organisations you choose, gathers evidence from the sources you approve, adds a recruiter screen and a '
            'consistency audit of your CV, LinkedIn and website, and re-scores as you act on the plan.</p></div>'
            '<div class="say">Say "run LVLme"</div></div></section>')


def render(result):
    r = result["role"]
    demo = " · fictional demo" if result.get("fictional") else ""
    foot = ("Drafts only: LVLme never applies, sends or posts for you. Your CV and this page stay on your computer. "
            "Inputs fingerprint %s." % esc(result["inputs_digest"][:19]))
    body = "".join([hero(result), factors(result), fixes(result), brief(result), checked(result), deeper()])
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"color-scheme\" content=\"light dark\">"
            "<title>LVLme quick: %s</title><style>%s</style></head><body><div class=\"wrap\">"
            "<header class=\"top\"><span class=\"mark\">%s</span><b>LVLme quick</b>"
            "<span class=\"sub\">%s%s</span></header><main>%s</main><footer>%s</footer></div></body></html>\n" % (
                esc("%s at %s" % (r["title"], r["org_name"])), CSS, LOGO, esc(long_date(result["date"])), demo, body, foot))
