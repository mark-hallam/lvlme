"""The shared page style for the static pages LVLme writes (the research pages and the demo index): one
self-contained stylesheet and a few helpers.

Inline CSS, no script, no external requests (no fonts, images or styles loaded from anywhere). Light by default,
with a dark mode that follows the device. The colours are the dashboard's tokens, so the pages look like one
product.

Accessibility (tests/test_page_a11y.py keeps it so): every text colour pair passes WCAG AA contrast in both
themes, no text is under 12px, the meters and bars stay visible in forced colours (Windows contrast themes), and
the device's "increase contrast" setting darkens the grey text.
"""
import html

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
a.posting,a.guide{padding:10px 4px;margin:0 -4px}
.wrap{max-width:780px;margin:0 auto;padding:20px 16px 48px}
.top{display:flex;align-items:center;gap:10px;margin:4px 2px 16px}
.mark{width:28px;height:28px;border-radius:8px;background:var(--accent);color:var(--on-accent);display:grid;place-items:center}
.mark svg{width:16px;height:16px}
.top b{font-size:17px;letter-spacing:-.01em;white-space:nowrap}
.top .sub{margin-left:auto;font-size:13px;text-align:right}.nw{white-space:nowrap}
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
.meter{display:grid;grid-template-columns:repeat(6,1fr);gap:4px}
.meter i{height:6px;border-radius:3px;background:var(--pip)}
.meter i.on{background:var(--accent)}
.meter-l{display:flex;justify-content:space-between;font-size:12px;color:var(--sub);margin-top:4px}
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
.gone{margin:10px 0 0}
table{border-collapse:collapse;width:100%;font-size:14px;margin-top:8px}
th,td{text-align:left;padding:7px 8px;border-top:1px solid var(--rule);vertical-align:top}
th{font-weight:600;color:var(--sub)}
.deeper{display:flex;gap:16px;align-items:center}
.say{margin:0;background:var(--accent-soft);border-radius:12px;padding:10px 16px;white-space:nowrap}
.say .k{display:block;font-size:12px;font-weight:600;color:var(--sub)}
.say b{font-size:17px;font-weight:650}
footer{margin-top:20px;font-size:13px;color:var(--sub);padding:0 4px}
footer details{margin-top:6px}footer summary{cursor:pointer}
@media (max-width:560px){h1{font-size:24px}.tile{padding:12px}.tile .b{font-size:21px}
.deeper{flex-direction:column;align-items:flex-start}.card{padding:18px 16px}.top .nw{display:block}.top .sep{display:none}}
@media (max-width:340px){.odds{grid-template-columns:1fr}th,td{padding:7px 4px}}
@media (prefers-contrast:more){:root{--sub:var(--ink);--rule:#8e8e93;--pip:#8e8e93}}
@media (prefers-contrast:more) and (prefers-color-scheme:dark){:root{--pip:#636366}}
@media (forced-colors:active){.card,.tile,.note,.all,.say,.banner,.chip,.mark,ol.fixes li::before{border:1px solid CanvasText}
.meter i,.pips i,.track{forced-color-adjust:none;background:Canvas;border:1px solid CanvasText}
.meter i.on,.pips i.on,.track .now{background:Highlight}
.track .maybe{background:repeating-linear-gradient(135deg,Highlight 0 2px,Canvas 2px 5px)}}
"""

LOGO = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 13 L6 7 L9 10 L14 3" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def long_date(iso):
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]
    y, m, d = iso.split("-")
    return "%d %s %s" % (int(d), months[int(m) - 1], y)


def chip(text, cls):
    return '<span class="chip %s">%s</span>' % (cls, esc(text))
