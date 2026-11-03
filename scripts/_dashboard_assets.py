"""The dashboard page (report/index.html): one template with inline CSS and JavaScript.

build_dashboard.py replaces __TITLE__ and __DATA__ (the JSON the page renders
from). The page makes no external requests: no fonts, scripts or images are
loaded from anywhere. Colours: one accent, a sequential blue ramp for the
chance bands and the heat map, and the validated colour-blind-safe
categorical palette for organisations, in config.json target order.
"""

# Categorical slots (light, dark), fixed order, never cycled. Colour follows
# the organisation (its position in config.json targets).
PALETTE = [
    ("#2a78d6", "#3987e5"), ("#eb6834", "#d95926"), ("#1baf7a", "#199e70"), ("#eda100", "#c98500"),
    ("#e87ba4", "#d55181"), ("#008300", "#008300"), ("#6250d6", "#9085e9"), ("#e34948", "#e66767"),
]
OTHER = ("#8e8e93", "#98989d")

CSS = r"""
:root{color-scheme:light;
 --bg:#f2f2f5;--card:#ffffff;--card2:#f6f6f8;--ink:#1d1d1f;--sub:#56565b;--line:#a9a9ae;--rule:#e2e2e7;
 --accent:#084c9e;--on-accent:#ffffff;--accent-soft:#e7f0fb;--ok:#0f5f2a;--warn:#843800;--warn-bg:#fff4d6;
 --z0:#f7f7f9;--z1:#efeff3;--grid:#e4e4e9;--shadow:0 1px 2px rgba(0,0,0,.04),0 8px 24px rgba(0,0,0,.06);
 --p0:#e6e6eb;--p0t:#2c2c2e;--p1:#d6e6fa;--p1t:#0d366b;--p2:#86b6ef;--p2t:#0b2447;--p3:#1b54a0;--p3t:#ffffff;--p4:#0b2a55;--p4t:#ffffff;
 --h0:#ececf0;--h1:#cde2fb;--h2:#86b6ef;--h3:#1b54a0;--h4:#133f7a;--h5:#0b2a55;--hlt:#0b2447;--hdt:#ffffff;
 --tv-bg:#dff3e4;--tv-t:#14501f;--tc-bg:#fde3e1;--tc-t:#7a1810;--tp-bg:#fcefd6;--tp-t:#6b3f00;
 --stop:#6e6e73;--link-soft:#084c9e;--ease:cubic-bezier(.22,1,.36,1);--spring:cubic-bezier(.34,1.25,.64,1)}
:root[data-theme=dark]{color-scheme:dark;
 --bg:#111113;--card:#1c1c1e;--card2:#26262a;--ink:#f5f5f7;--sub:#b8b8be;--line:#8e8e93;--rule:#38383c;
 --accent:#64b0ff;--on-accent:#0b1a2b;--accent-soft:#172c45;--ok:#4cd964;--warn:#ffb340;--warn-bg:#3a2e0b;
 --z0:#1f1f22;--z1:#252529;--grid:#323236;--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.4);
 --p0:#3a3a3e;--p0t:#f2f2f7;--p1:#1b54a0;--p1t:#ffffff;--p2:#78aeee;--p2t:#0b1a2b;--p3:#9cc4f3;--p3t:#0b1a2b;--p4:#cfe2fa;--p4t:#0b1a2b;
 --h0:#2c2c30;--h1:#163f75;--h2:#2a6bc4;--h3:#78aeee;--h4:#9cc4f3;--h5:#cfe2fa;--hlt:#ffffff;--hdt:#0b1a2b;
 --tv-bg:#1e3a24;--tv-t:#a6efb0;--tc-bg:#3d1714;--tc-t:#ffc2ba;--tp-bg:#3a2a10;--tp-t:#ffd99a;--link-soft:#8cc4ff;--stop:#9a9aa0}
*{box-sizing:border-box}
[hidden]{display:none!important}
html,body{margin:0;background:var(--bg);color:var(--ink)}
body{font:16px/1.55 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;overflow-wrap:break-word;overflow-x:hidden}
button{font:inherit;color:inherit}
a{color:var(--accent)}
.sub{color:var(--sub)}.small{font-size:14px}.tiny{font-size:13px}
.sr-only{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.num{font-variant-numeric:tabular-nums}

/* header */
.top{position:sticky;top:0;z-index:30;background:var(--bg);border-bottom:1px solid var(--rule)}
.top-in{max-width:1520px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:12px}
.brand{display:flex;flex-direction:column;min-width:0;flex:1}
.brand h1{font-size:17px;font-weight:700;letter-spacing:-.01em;line-height:1.3;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.brand span{font-size:13px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.btn{border:1px solid var(--rule);background:var(--card);border-radius:999px;padding:7px 14px;cursor:pointer;font-size:14px;font-weight:500}
.btn:hover{background:var(--card2)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.banner{max-width:1520px;margin:12px auto 0;padding:0 20px}
.banner div{background:var(--warn-bg);color:var(--warn);border-radius:12px;padding:9px 14px;font-size:14px;font-weight:550}

/* segmented controls */
.seg{display:inline-flex;background:var(--card2);border:1px solid var(--rule);border-radius:11px;padding:3px;gap:2px;overflow-x:auto;max-width:100%;scrollbar-width:none}
.seg::-webkit-scrollbar{display:none}
.seg button{border:none;background:none;padding:6px 12px;border-radius:8px;font-size:14px;font-weight:500;color:var(--sub);cursor:pointer;white-space:nowrap}
.seg button[aria-pressed=true],.seg button[aria-selected=true]{background:var(--card);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.seg.small button{padding:4px 10px;font-size:13px}
/* a row that scrolls sideways shows a fade and a chevron while there is more to see */
.hscroll{position:relative;display:inline-flex;max-width:100%;vertical-align:top}
.hscroll::before,.hscroll::after{position:absolute;top:1px;bottom:1px;pointer-events:none;opacity:0;transition:opacity .2s}
.hscroll::after{content:"\203A";right:1px;width:52px;display:flex;align-items:center;justify-content:flex-end;padding-right:10px;font-size:24px;font-weight:600;color:var(--accent);background:linear-gradient(to right,rgba(246,246,248,0),var(--card2) 60%);border-radius:0 11px 11px 0}
.hscroll::before{content:"";left:1px;width:28px;background:linear-gradient(to left,rgba(246,246,248,0),var(--card2));border-radius:11px 0 0 11px}
:root[data-theme=dark] .hscroll::after{background:linear-gradient(to right,rgba(38,38,42,0),var(--card2) 60%)}
:root[data-theme=dark] .hscroll::before{background:linear-gradient(to left,rgba(38,38,42,0),var(--card2))}
.hscroll.more-right::after,.hscroll.more-left::before{opacity:1}

/* layout */
.app{max-width:1520px;margin:0 auto;padding:20px;display:grid;grid-template-columns:272px minmax(0,1fr) 340px;gap:20px;align-items:start}
.centre{container-type:inline-size;min-width:0}
@media (min-width:1280px){.centre .pair,.hero .next-in{display:none}}
.next-in{margin:16px 0 0;padding:14px 0 8px;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
@media (min-width:1500px){.app{grid-template-columns:300px minmax(0,1fr) 380px}}
.rail,.detail{position:sticky;top:76px;max-height:calc(100vh - 96px);overflow:auto;scrollbar-width:thin}
.card{background:var(--card);border-radius:18px;box-shadow:var(--shadow);padding:18px 20px}
.card+.card{margin-top:16px}
.eyebrow{font-size:13px;font-weight:650;color:var(--sub);letter-spacing:.03em;margin-bottom:8px;text-transform:uppercase}
h2{font-size:22px;letter-spacing:-.015em;margin:0 0 6px}
h3{font-size:17px;margin:0 0 6px}
.rail-h,.pane-h{font-size:17px;letter-spacing:0;margin:0 0 6px}

/* rail */
.sw{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-top:1px solid var(--rule)}
.sw:first-child{border-top:none}
.sw-main{flex:1;min-width:0}
.sw-title{font-size:15px;font-weight:550;line-height:1.35;cursor:pointer}
.sw-title:hover{color:var(--accent)}
.sw-lift{font-size:13px;margin-top:3px}
.sw-lift b{color:var(--ok)}
.sw-meta{font-size:13px;color:var(--sub);margin-top:2px}
.stale{color:var(--warn);font-weight:600}
.tog{position:relative;width:44px;height:26px;flex-shrink:0;border-radius:999px;background:var(--rule);border:none;cursor:pointer;margin-top:2px}
.tog::before{content:"";position:absolute;inset:-9px 0}
.tog::after{content:"";position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.3)}
.tog[aria-checked=true]{background:var(--ok)}
.tog[aria-checked=true]::after{transform:translateX(18px)}
.rail-actions{display:flex;gap:8px;margin:6px 0 4px}
.metric{display:flex;justify-content:space-between;align-items:baseline;padding:9px 0;border-top:1px solid var(--rule);font-size:15px;gap:8px}
.metric:first-child{border-top:none}
.metric b{font-size:18px}
.metric > .num{white-space:nowrap}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle;background:var(--line)}
.dn-tag{color:var(--accent);font-weight:600}
.dn .status-dot{margin-right:0;flex-shrink:0}
.status-dot.doing{background:var(--accent)}.status-dot.done{background:var(--ok)}
.grp-h{display:flex;justify-content:space-between;align-items:baseline;font-size:13px;font-weight:650;color:var(--sub);letter-spacing:.03em;text-transform:uppercase;margin:12px 0 0}
.grp{border-top:1px solid var(--rule);margin-top:6px}
.grp summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;padding:12px 0 4px;font-size:13px;font-weight:650;color:var(--sub);letter-spacing:.03em;text-transform:uppercase}
.grp summary::-webkit-details-marker{display:none}
.grp summary .chev{display:inline-block}
.grp[open] summary .chev{transform:rotate(90deg)}
.grp-note{font-size:13px;color:var(--sub);margin:2px 0 4px;text-transform:none;letter-spacing:0;font-weight:400}
.done-tick{width:26px;height:26px;border-radius:50%;background:var(--ok);color:#fff;display:grid;place-items:center;font-size:14px;flex-shrink:0;margin-top:2px}

/* hero */
.strip{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--sub);padding:0 0 14px;border-bottom:1px solid var(--rule);margin-bottom:16px}
.strip b{color:var(--ink);font-size:14px;margin-left:4px}
.hero-row{display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;align-items:flex-start}
.hero-row > div:first-child{flex:1 1 230px;min-width:0}
.best-l{font-size:14px;color:var(--sub);font-weight:500}
.best-v{font-size:56px;font-weight:700;letter-spacing:-.03em;line-height:1.05}
.best-v small{font-size:22px;color:var(--sub);font-weight:500;letter-spacing:0}
.best-pills{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:6px;font-size:13px;color:var(--sub)}
.level{background:var(--card2);border-radius:16px;padding:12px 14px;flex:1 1 240px;max-width:330px}
.level-top{display:flex;align-items:center;gap:10px}
.level-badge{width:44px;height:44px;border-radius:12px;background:var(--accent);color:var(--on-accent);display:grid;place-items:center;font-weight:750;font-size:20px;flex-shrink:0}
.level-name{font-weight:650}
.prog{height:8px;border-radius:4px;background:var(--rule);overflow:hidden;margin:10px 0 6px}
.prog span{display:block;height:100%;background:var(--accent);border-radius:4px;transform-origin:left}
.controls{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;align-items:center;margin:16px 0 6px}
.pill{display:inline-block;font-size:12px;font-weight:650;padding:2px 9px;border-radius:999px;white-space:nowrap}
.pb0{background:var(--p0);color:var(--p0t)}.pb1{background:var(--p1);color:var(--p1t)}.pb2{background:var(--p2);color:var(--p2t)}.pb3{background:var(--p3);color:var(--p3t)}.pb4{background:var(--p4);color:var(--p4t)}
.chart-wrap{position:relative;margin-top:6px}
.chart-wrap svg{width:100%;height:auto;display:block;overflow:visible}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--sub);margin:10px 0 0}
.legend span{display:inline-flex;align-items:center;gap:6px}
.lk{width:18px;height:0;border-top:2px solid currentColor;display:inline-block}
.zone-label{fill:var(--ink);font-size:12px;font-weight:650}
.axis{fill:var(--sub);font-size:11px}
.gridline{stroke:var(--grid);stroke-width:1}
.series{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.wp{cursor:pointer}
.hit{fill:transparent;cursor:crosshair}
.cross{stroke:var(--line);stroke-width:1;stroke-dasharray:3 3}
.tiles3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}
.tile3{background:var(--card2);border-radius:14px;padding:12px 14px}
.tile3 .l{font-size:13px;color:var(--sub)}
.tile3 .v{font-size:30px;font-weight:700;letter-spacing:-.02em;line-height:1.15;margin:2px 0 4px}
.history{display:flex;gap:10px;overflow-x:auto;padding:10px 0 2px;scrollbar-width:thin}
.run-chip{flex-shrink:0;background:var(--card2);border-radius:12px;padding:8px 12px;font-size:13px;border:1px solid transparent}
.run-chip.sample{border:1px dashed var(--line)}
.run-chip b{font-size:15px}
.switch-row{display:flex;align-items:center;gap:10px;font-size:14px;color:var(--sub);margin-top:12px;flex-wrap:wrap}
.tableview{margin-top:12px;font-size:14px}
.tableview summary{cursor:pointer;color:var(--accent);font-weight:550}
table{border-collapse:collapse;width:100%}
.tscroll{overflow-x:auto;max-width:100%}
td,th{text-align:left;padding:7px 6px;border-top:1px solid var(--rule);vertical-align:top}
th{font-size:13px;color:var(--sub);font-weight:650}

/* below the hero */
.tiles4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:16px}
.tiles5{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:14px}
.tile{background:var(--card);border-radius:16px;box-shadow:var(--shadow);padding:14px 16px}
.tile .v{font-size:28px;font-weight:700;letter-spacing:-.02em}
.tile .l{font-size:13px;color:var(--sub)}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.grid2 > .card,.grid2 > .list{margin-top:0}
.pair{margin-top:16px}
.dn{display:flex;gap:12px;align-items:center;padding:11px 0;border-top:1px solid var(--rule);cursor:pointer}
.dn:first-of-type{border-top:none}
.dn:hover .dn-t{color:var(--accent)}
.dn-t{font-weight:550;font-size:15px;line-height:1.35}
.dn-p{font-weight:700;color:var(--ok);font-variant-numeric:tabular-nums;white-space:nowrap}
.linkbtn{border:none;background:none;color:var(--accent);cursor:pointer;padding:0;font-size:14px;font-weight:550}
/* warm paths: one strip per organisation, five steps from followed to would refer (progress only, no score reads it) */
.wp{padding:10px 0;border-top:1px solid var(--rule)}
.wp:first-child{border-top:none}
.wp[data-org-open]{cursor:pointer}
.wp[data-org-open]:hover .wp-n,.wp[data-org-open]:focus .wp-n{color:var(--accent)}
.wp-h{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.wp-n{font-weight:550;font-size:15px;line-height:1.35}
.wp-s{font-size:13px;font-weight:650;color:var(--accent);white-space:nowrap}
.wp-s.none{color:var(--sub);font-weight:500}
.wp-bar{display:flex;gap:3px;margin:6px 0 4px}
.wp-bar i{flex:1;height:6px;border-radius:3px;background:var(--p0)}
.wp-bar i.on{background:var(--accent)}
.wp-c{padding:8px 0;border-top:1px solid var(--rule)}

/* views */
.views-nav{margin:24px 0 14px;position:sticky;top:calc(var(--top-h, 60px) + 4px);z-index:5}
@media (min-width:760px){.views-nav .seg{flex-wrap:wrap;overflow:visible}}
.view{display:none}
.view.on{display:block}
.org-card{cursor:pointer}
.org-head{display:flex;gap:14px;align-items:center}
.org-name{font-weight:700;font-size:17px;display:flex;align-items:center;gap:8px}
.org-key{width:14px;height:4px;border-radius:2px;display:inline-block;flex-shrink:0}
.ring-num{font-size:20px;font-weight:700;fill:var(--ink)}
.kv{display:flex;justify-content:space-between;align-items:center;font-size:14px;color:var(--sub);padding:4px 0;gap:8px}
.kv b{color:var(--ink)}
.list{background:var(--card);border-radius:18px;box-shadow:var(--shadow);overflow:hidden}
.row{display:flex;gap:12px;align-items:center;padding:13px 18px;border-top:1px solid var(--rule);cursor:pointer}
.row:first-child{border-top:none}
.row:hover{background:var(--card2)}
.row-main{flex:1;min-width:0}
.row-title{font-weight:600;line-height:1.35}
.row-sub{font-size:14px;color:var(--sub)}
.row-side{text-align:right;flex-shrink:0;font-variant-numeric:tabular-nums}
.chev{color:var(--sub);font-size:20px;line-height:1}
.filters{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
select{font:inherit;font-size:14px;padding:7px 10px;border-radius:10px;border:1px solid var(--rule);background:var(--card);color:var(--ink);max-width:100%}
.gbar{display:grid;grid-template-columns:minmax(120px,38%) 1fr;gap:12px;align-items:center;padding:10px 0;border-top:1px solid var(--rule);outline:none}
.gbar:first-child{border-top:none}
.gtrack{display:flex;align-items:center;gap:10px;min-width:0}
.gfill{height:14px;background:var(--accent);border-radius:0 4px 4px 0;transform-origin:left}
.gbar:hover .gfill,.gbar:focus .gfill{filter:brightness(1.12)}
.heat{width:100%;border-collapse:separate;border-spacing:3px 3px;font-size:13px}
.heat th{border:none;font-size:12px;text-align:center;padding:4px 2px;vertical-align:bottom;position:sticky;top:0;background:var(--card)}
.heat th:first-child{text-align:left}
.heat td{border:none;padding:0}
.heat .name{padding:6px 8px 6px 0;cursor:pointer;min-width:180px}
.heat .name:hover .row-title{color:var(--accent)}
.cell{display:grid;place-items:center;height:30px;min-width:34px;border-radius:6px;font-weight:650;font-variant-numeric:tabular-nums;cursor:default}
.cell.nj{background:transparent;color:var(--sub);border:1px dashed var(--line);font-weight:500;white-space:nowrap;padding:0 6px}
.heat-wrap{overflow-x:auto}
.tag{display:inline-block;font-size:12px;font-weight:650;padding:1px 8px;border-radius:7px;background:var(--card2);color:var(--sub);white-space:nowrap}
.t-verified,.t-corroborated,.t-supported{background:var(--tv-bg);color:var(--tv-t)}
.t-contradicted,.t-unsupported{background:var(--tc-bg);color:var(--tc-t)}
.t-self_reported,.t-partially_verified,.t-overstated{background:var(--tp-bg);color:var(--tp-t)}
.static-sum h2{font-size:17px;margin:2px 0 4px}.static-sum h3{font-size:15px;margin:16px 0 6px}
.static-sum table{width:100%;border-collapse:collapse;font-size:14px}
.static-sum th,.static-sum td{text-align:left;padding:7px 8px 7px 0;border-top:1px solid var(--rule);vertical-align:top}
.static-sum thead th{border-top:none;font-size:12px;color:var(--sub);font-weight:650}
.static-sum ol{margin:4px 0 0;padding-left:22px}.static-sum li{margin:6px 0}
.static-sum .num{font-variant-numeric:tabular-nums}
.chip{display:inline-block;border:1px solid var(--rule);background:var(--card2);border-radius:999px;padding:2px 10px;font-size:13px;margin:3px 4px 0 0;cursor:pointer;color:var(--ink)}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip.plain{cursor:default}.chip.plain:hover{border-color:var(--rule);color:var(--ink)}
.swot-q ul{margin:6px 0 0;padding-left:18px}.swot-q li{margin:8px 0}
.tows{display:grid;grid-template-columns:auto 1fr;gap:10px 14px;align-items:start}
.tows .k{font-weight:750;color:var(--accent)}
.grids details{margin-top:16px}
.grids summary{cursor:pointer;font-weight:650;color:var(--accent);margin-bottom:8px}
.badges{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.badge{border:1px solid var(--rule);border-radius:16px;padding:12px;text-align:center;cursor:pointer;background:var(--card)}
.badge .bi{width:46px;height:46px;border-radius:50%;margin:0 auto 8px;display:grid;place-items:center;font-size:20px;font-weight:700;background:var(--card2);color:var(--sub);border:2px dashed var(--line)}
.badge.doing .bi{border:2px solid var(--accent);color:var(--ink);background:var(--accent-soft)}
.badge.done .bi{background:var(--ok);color:#fff;border:2px solid var(--ok)}
.badge .bt{font-size:13px;font-weight:600;line-height:1.3}
.badge .bs{font-size:12px;color:var(--sub);margin-top:2px}

/* path to the top band */
.p90-tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:14px}
.p90-row{display:grid;grid-template-columns:minmax(0,40%) minmax(0,1fr);gap:2px 16px;align-items:center;padding:9px 0;border-top:1px solid var(--rule);outline:none}
.p90-row[data-role-open]{cursor:pointer}
.p90-row:first-child{border-top:none}
.p90-row:hover .p90-name,.p90-row:focus .p90-name{color:var(--accent)}
.p90-name{font-size:14px;font-weight:600;line-height:1.3}
.p90-nums{margin-top:1px}.p90-nums b{color:var(--ink)}
.p90-track{position:relative;height:26px}
.p90-track .base{position:absolute;left:0;right:0;top:12px;height:2px;background:var(--rule);border-radius:1px}
.p90-track .span{position:absolute;top:11px;height:4px;border-radius:2px;opacity:.45}
.p90-track .ext{position:absolute;top:12px;height:0;border-top:2px dashed var(--line)}
.p90-track .mk{position:absolute;top:13px;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;box-sizing:border-box}
.mk.now{background:var(--ink);border:2px solid var(--card)}
.mk.likely{border:2px solid var(--card)}
.mk.ceil{background:var(--card);border:2.5px solid var(--ink)}
.mk.hist{background:var(--card);border:2px dashed var(--line)}
.p90-guide{position:absolute;top:0;bottom:0;width:0}
.p90-guide.g70{border-left:1.5px dashed var(--ok)}
.p90-guide.gt{border-left:1.5px solid var(--accent)}
.p90-axis-row{display:grid;grid-template-columns:minmax(0,40%) minmax(0,1fr);gap:2px 16px;padding-top:4px;border-top:1px solid var(--rule)}
.p90-axis{position:relative;height:20px;font-size:11px;color:var(--sub)}
.p90-axis span{position:absolute;top:3px;transform:translateX(-50%);white-space:nowrap}
.p90-key{display:inline-block;width:12px;height:12px;border-radius:50%;box-sizing:border-box;vertical-align:-1px}
.f5-k{font-size:13px;font-weight:650;color:var(--sub);margin-top:12px}
.f5 ul{margin:4px 0 0;padding-left:18px}.f5 li{margin:4px 0}
.phases{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.phase{background:var(--card2);border-radius:14px;padding:12px 14px}
.phase .ph-n{font-weight:700}
.phase ul{margin:6px 0 0;padding-left:18px;font-size:14px}.phase li{margin:4px 0}
.rm{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:8px 0 16px}
.rm > div{background:var(--card2);border-radius:12px;padding:8px 10px}
.rm b{font-size:22px;letter-spacing:-.02em;display:block;line-height:1.2}
.odds{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:10px 0 4px}
.odds > div{background:var(--card2);border-radius:14px;padding:12px 14px}
.odds b{display:block;font-size:24px;letter-spacing:-.02em;line-height:1.2;margin-top:2px}
.watch ul{margin:4px 0 0;padding-left:18px}.watch li{margin:3px 0}
@container (max-width:680px){.p90-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
@container (max-width:560px){.p90-row{grid-template-columns:minmax(0,1fr)}.p90-axis-row{grid-template-columns:minmax(0,1fr)!important}.p90-axis-row > div:first-child{display:none}}
@container (max-width:470px){.odds{grid-template-columns:minmax(0,1fr)}}

/* level up: the next level, quests, level history and streak */
.level .lv-line{margin-top:6px;color:var(--ink);line-height:1.4}
.level .linkbtn{margin-top:6px;font-size:13px;color:var(--link-soft)}
.lv-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
.lv-head h3{margin:2px 0 4px}
.lv-need{text-align:right;flex-shrink:0}
.lv-need b{display:block;font-size:34px;letter-spacing:-.02em;line-height:1.05}
.lv-track{position:relative;height:30px;margin:18px 0 0}
.lv-zone{position:absolute;top:0;right:0;height:30px;border-radius:7px;background:var(--tv-bg)}
.lv-base,.lv-fill,.lv-exp{position:absolute;top:12px;height:6px;border-radius:3px}
.lv-base{left:0;right:0;background:var(--rule)}
.lv-fill{left:0;background:var(--accent);transform-origin:left}
.lv-exp{background:var(--accent);opacity:.38}
.lv-bx{position:absolute;top:14px;height:0;border-top:2px dashed var(--accent)}
.lv-goal{position:absolute;top:-3px;bottom:-3px;width:0;border-left:2px solid var(--ok)}
.lv-mk{position:absolute;top:15px;width:12px;height:12px;margin:-6px 0 0 -6px;box-sizing:border-box}
.lv-mk.now{width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;background:var(--ink);border:2px solid var(--card)}
.lv-mk.exp{background:var(--accent);border:2px solid var(--card);transform:rotate(45deg)}
.lv-mk.best{background:var(--card);border:2px solid var(--accent);transform:rotate(45deg)}
.lv-axis{position:relative;height:20px;font-size:12px;color:var(--sub);margin-top:2px}
.lv-axis span{position:absolute;top:2px;transform:translateX(-50%);white-space:nowrap}
.lv-axis .goal{color:var(--ok);font-weight:700}
.lv-key{display:inline-block;width:10px;height:10px;transform:rotate(45deg);box-sizing:border-box}
.lv-key.exp{background:var(--accent)}.lv-key.best{background:var(--card);border:2px solid var(--accent)}
.lv-verdict{margin-top:14px;padding-top:14px;border-top:1px solid var(--rule)}
.lv-v-h{font-weight:700;font-size:17px;margin-bottom:4px}
.lv-verdict p{margin:4px 0}
.lv-set{margin-top:8px}
.lv-step{display:flex;gap:10px;align-items:center;padding:9px 0;border-top:1px solid var(--rule);cursor:pointer}
.lv-step:first-child{border-top:none}
.lv-step-t{flex:1;min-width:0;font-weight:600;font-size:15px;line-height:1.35}
.lv-step:hover .lv-step-t,.lv-step:focus .lv-step-t{color:var(--accent)}
.lv-step .tiny{white-space:nowrap}
.lv-room{display:flex;align-items:baseline;gap:10px;padding:8px 0;border-top:1px solid var(--rule)}
.lv-room:first-child{border-top:none}
.lv-room > span:first-child{flex:1;min-width:0}
.lv-room b{font-variant-numeric:tabular-nums;white-space:nowrap}
.tag.crit{background:var(--accent);color:var(--on-accent)}
.tag.pend{background:var(--warn-bg);color:var(--warn)}
.tag.up{background:var(--tv-bg);color:var(--tv-t)}.tag.down{background:var(--tc-bg);color:var(--tc-t)}
.quests{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.quest{background:var(--card);border-radius:16px;box-shadow:var(--shadow);padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-width:0}
.quest.crit{box-shadow:inset 0 0 0 2px var(--accent),var(--shadow)}
.q-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.q-tags{display:flex;flex-wrap:wrap;gap:4px;min-width:0}
.q-id{font-size:13px;color:var(--sub);white-space:nowrap}
.q-title{font-weight:650;font-size:16px;line-height:1.35;cursor:pointer}
.q-title:hover,.q-title:focus{color:var(--accent)}
.q-pts{display:flex;flex-wrap:wrap;gap:2px 16px;align-items:baseline}
.q-pts b{font-size:22px;letter-spacing:-.02em;color:var(--ok)}
.q-pts b.q-alt{font-size:17px;color:var(--ink)}
.q-meta{font-size:13px;color:var(--sub)}
.q-foot{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin-top:auto;padding-top:10px;border-top:1px solid var(--rule)}
.q-msg{font-size:13px;color:var(--sub)}
.q-msg:empty{display:none}
.q-text{display:block;margin-top:4px;padding:8px 10px;border-radius:10px;background:var(--card2);border:1px solid var(--rule);color:var(--ink);font-size:13px;user-select:all;overflow-wrap:anywhere}
.pend-box{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--sub);cursor:pointer}
.pend-box input{width:18px;height:18px;margin:0;accent-color:var(--warn)}
.streak{display:flex;gap:14px;align-items:center}
.streak-n{font-size:44px;font-weight:750;letter-spacing:-.03em;line-height:1;color:var(--ok);min-width:44px;text-align:center}
.streak-n.zero{color:var(--sub)}
.streak-dots{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 2px}
.sd{width:14px;height:14px;border-radius:50%;border:2px solid var(--line);box-sizing:border-box}
.sd.on{background:var(--ok);border-color:var(--ok)}
.sd.start{border-style:dashed}
.lh-row{display:grid;grid-template-columns:auto auto minmax(0,1fr);gap:2px 12px;align-items:center;padding:10px 0;border-top:1px solid var(--rule)}
.lh-row:first-child{border-top:none}
.lh-date{white-space:nowrap;min-width:84px}
.lv-badge{width:28px;height:28px;border-radius:8px;background:var(--accent);color:var(--on-accent);display:grid;place-items:center;font-weight:750;font-size:14px}
.run-chip .tag{margin-left:4px}
.animate .enter .lvl-pop,.animate .lvl-pop.enter{animation:pop .6s var(--spring)}
.animate .enter .lv-fill{animation:grow .8s var(--ease)}
@container (max-width:620px){.quests{grid-template-columns:minmax(0,1fr)}.lv-need b{font-size:28px}}
.lv-legend{margin-top:6px;row-gap:6px}
@container (max-width:420px){.lh-row{grid-template-columns:auto minmax(0,1fr)}.lh-date{grid-column:1/-1;min-width:0}.lv-head{flex-direction:column;gap:6px}.lv-need{text-align:left}.lv-need b{display:inline;font-size:26px;margin-right:6px}.lv-step{flex-wrap:wrap}.lv-step .tiny{width:100%;padding-left:2px}}

/* detail pane */
.crumbs{display:flex;flex-wrap:wrap;gap:4px;align-items:center;font-size:13px;margin-bottom:12px}
.crumbs button{border:none;background:none;color:var(--accent);cursor:pointer;padding:2px 4px;border-radius:6px}
.crumbs button:last-child{color:var(--ink);font-weight:650;cursor:default}
.crumbs .sep{color:var(--sub)}
.d-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.close{border:1px solid var(--rule);background:var(--card2);width:30px;height:30px;border-radius:50%;cursor:pointer;flex-shrink:0;font-size:15px;line-height:1;color:var(--ink)}
.factor{padding:11px 0;border-top:1px solid var(--rule);cursor:pointer}
.factor:hover .factor-name{color:var(--accent)}
.factor-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.factor-name{font-weight:650;font-size:15px}
.dots{display:inline-flex;gap:4px}
.dots i{width:12px;height:12px;border-radius:50%;background:var(--rule);display:inline-block}
.dots i.on{background:var(--accent)}.dots i.proj{background:transparent;box-shadow:inset 0 0 0 2px var(--ok)}
.journey-mini{display:flex;align-items:baseline;gap:8px;margin:10px 0 4px;font-variant-numeric:tabular-nums}
.journey-mini b{font-size:24px;letter-spacing:-.02em}
.arrow{color:var(--sub)}
.warnline{margin-top:8px;color:var(--warn);font-weight:550}

/* tooltip, scrim, modal */
.tip{position:fixed;pointer-events:none;z-index:60;background:var(--card);color:var(--ink);border:1px solid var(--rule);border-radius:10px;padding:9px 11px;font-size:13px;box-shadow:var(--shadow);display:none;min-width:150px;max-width:300px}
.tip .tv{font-weight:750;font-size:14px}.tip .tn{color:var(--sub)}
.tip-row{display:flex;align-items:center;gap:6px;margin-top:3px}
.scrim{position:fixed;inset:0;background:rgba(0,0,0,.32);display:none;z-index:35}
.scrim.on{display:block}
.bottombar{display:none}
.modal{position:fixed;inset:0;display:none;place-items:center;z-index:50}
.modal.on{display:grid}
.modal .panel{background:var(--card);border-radius:22px;box-shadow:0 20px 60px rgba(0,0,0,.3);width:min(640px,94vw);padding:22px}
.share-card{border-radius:18px;padding:22px;background:var(--card2);border:1px solid var(--rule);margin:12px 0}
.share-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}
.share-row div{background:var(--card);border-radius:12px;padding:10px 12px;min-width:0}
.share-row b{display:block;font-size:28px;letter-spacing:-.02em}
.share-row .pill{white-space:normal;max-width:100%;overflow-wrap:normal}

/* motion: only while .animate is on the body (visible tab, motion allowed); every
   animated element also loses its .enter class on a timer, so nothing stays hidden */
.animate .enter.view,.animate .enter .d-body{animation:fade .34s var(--ease)}
.animate .enter .gfill,.animate .enter .prog span{animation:grow .8s var(--ease)}
.animate .enter .reveal{animation:grow 1.1s var(--ease)}
.animate .enter .ring-arc{animation:ring 1s var(--ease)}
.animate .enter .badge.done .bi{animation:pop .5s var(--spring)}
.animate .tog::after{transition:transform .3s var(--spring)}
.animate .detail.slide{transition:transform .38s var(--spring)}
.animate .rail.slide{transition:transform .4s var(--spring)}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes ring{from{opacity:0}to{opacity:1}}
@keyframes pop{0%{transform:scale(.6)}100%{transform:scale(1)}}
.reveal{transform-box:fill-box;transform-origin:left center}

/* responsive */
@media (max-width:1279px){
 .app{grid-template-columns:280px minmax(0,1fr)}
 .detail{position:fixed;top:0;right:0;bottom:0;width:min(420px,94vw);max-height:none;z-index:40;border-radius:0;transform:translateX(105%);box-shadow:-12px 0 40px rgba(0,0,0,.2);background:var(--bg)}
 .detail.open{transform:none}
}
@media (max-width:999px){.tiles4{grid-template-columns:repeat(2,minmax(0,1fr))}}
@container (max-width:680px){.tiles4{grid-template-columns:repeat(2,minmax(0,1fr))}}
@container (max-width:470px){.tiles3{grid-template-columns:minmax(0,1fr)}}
@media (max-width:759px){
 .app{grid-template-columns:minmax(0,1fr);padding:14px 16px calc(92px + env(safe-area-inset-bottom))}
 .banner{padding:0 16px}
 .rail{position:fixed;left:0;right:0;bottom:0;top:auto;max-height:80vh;z-index:40;border-radius:22px 22px 0 0;transform:translateY(105%);padding:4px 10px 20px;background:var(--bg);box-shadow:0 -10px 40px rgba(0,0,0,.2)}
 .rail.open{transform:none}
 /* a real toolbar, not a floating button: the page reserves its height, so it never covers content */
 .bottombar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:36;align-items:center;gap:12px;padding:10px 16px calc(10px + env(safe-area-inset-bottom));background:var(--card);border-top:1px solid var(--rule)}
 .bb-text{flex:1;min-width:0;font-size:13px;color:var(--sub);line-height:1.3}
 .bb-text b{display:block;color:var(--ink);font-size:15px}
 .detail{top:auto;left:0;width:100%;height:88vh;border-radius:22px 22px 0 0;transform:translateY(105%)}
 .grid2{grid-template-columns:minmax(0,1fr)}
 .tiles3{grid-template-columns:minmax(0,1fr)}
 .best-v{font-size:46px}
 .level{max-width:none}
 .brand span{display:none}
 .share-row{gap:8px}
 .share-row div{padding:8px 9px}
 .share-row b{font-size:22px}
}
@media (max-width:759px){
 .btn,.seg button,select{min-height:44px}
 .seg.small button{min-width:44px}
 .linkbtn{min-height:44px;display:inline-flex;align-items:center}
 .close{width:44px;height:44px}
 #modeSeg{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));width:100%}
 #modeSeg button{white-space:normal;line-height:1.2;padding:4px 6px}
 .hscroll,.hscroll > .seg{width:100%}
 .banner div{font-size:13px;padding:8px 12px}
 .strip{padding-bottom:10px;margin-bottom:12px}
 .hero-row{gap:12px}
 .level{padding:10px 12px}
 .level .linkbtn{margin-top:0}
}
@media (max-width:420px){.top-in{padding:10px 16px;gap:10px}.brand h1{font-size:16px}.seg.small button{padding:4px 8px}.top .btn{padding:6px 12px}.card{padding:16px}.tiles4{gap:10px}.tile .v{font-size:24px}}
@media (max-width:360px){.seg button{padding:6px 8px;font-size:13px}}
@media (max-width:420px){.share-row div{padding:8px 7px}.share-row b{font-size:20px}.share-row .pill{font-size:11px;padding:2px 6px}}
@media (max-width:360px){.share-row{gap:6px}.share-row div{padding:8px 6px}.share-row .pill{padding:2px 5px}}
@media (max-width:359px){.share-row{grid-template-columns:minmax(0,1fr)}}
.sheet-grip{display:none;width:40px;height:5px;border-radius:3px;background:var(--line);margin:8px auto 4px}
.sheet-done{display:none}
@media (max-width:759px){.sheet-grip{display:block}.sheet-done{display:block;margin:0 4px 8px auto}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
"""

BODY = r"""
<header class="top"><div class="top-in">
 <div class="brand"><h1 id="brandTitle">__TITLE__</h1><span id="storyLine"></span></div>
 <div class="seg small" id="themeSeg" role="group" aria-label="Appearance"><button data-t="light" aria-pressed="true">Light</button><button data-t="dark" aria-pressed="false">Dark</button></div>
 <button class="btn primary" id="shareBtn">Share</button>
</div></header>
<div class="banner" id="banner" hidden><div id="bannerText"></div></div>

<div class="app">
 <aside class="rail" id="rail" aria-label="What if">
  <div class="sheet-grip"></div>
  <button class="btn sheet-done" id="railDone">Done</button>
  <div class="card">
   <div class="eyebrow">What if</div>
   <h2 class="rail-h">Switch plan actions on and off</h2>
   <p class="small sub" style="margin:2px 0 6px">Every number on the page updates. Each switch shows what that action adds to your best role with everything else on, and how many roles it lifts.</p>
   <div class="rail-actions"><button class="btn" id="allOn">All on</button><button class="btn" id="allOff">All off</button></div>
   <div class="grp-h"><span>Now</span><span class="tiny" id="nowCount"></span></div>
   <div class="grp-note">The open actions, in the same order as Do next. Work these first.</div>
   <div id="switchesNow"></div>
   <details class="grp" id="laterBox"><summary><span id="laterLabel">Later</span><span class="chev">›</span></summary><div class="grp-note">Over the active cap, or parked for later. Parked actions start switched off; any action here counts in the projection only while switched on.</div><div id="switchesLater"></div></details>
   <details class="grp" id="doneBox" hidden><summary><span id="doneLabel">Done</span><span class="chev">›</span></summary><div class="grp-note">Already in today's scores.</div><div id="switchesDone"></div></details>
  </div>
  <div class="card">
   <h2 class="eyebrow">Campaign progress</h2>
   <div id="metrics"></div>
  </div>
 </aside>

 <main class="centre" id="centre">
  <section class="card hero enter" id="hero" aria-labelledby="heroH">
   <h2 class="sr-only" id="heroH">Journey</h2>
   <div class="strip" id="strip"></div>
   <div class="hero-row">
    <div>
     <div class="best-l" id="bestLabel">Best match today</div>
     <div class="best-v num"><span id="bestNum">__BESTFIT__</span> <small>of 100</small></div>
     <div class="best-pills" id="bestPills"></div>
     <div class="small sub" id="bestRole" style="margin-top:6px">__BESTROLE__</div>
    </div>
    <div class="level" id="level">__LEVELCARD__</div>
   </div>
   <div class="next-in" id="nextIn" hidden><div class="eyebrow">Start here</div><h2 class="pane-h">Do next</h2><div id="doNext"></div></div>
   <div class="controls">
    <div class="seg" id="modeSeg" role="group" aria-label="Which numbers to show"></div>
    <div class="hscroll"><div class="seg" id="orgSeg" role="group" aria-label="Which organisation the journey follows"></div></div>
   </div>
   <div class="chart-wrap" id="chartWrap"></div>
   <div class="legend" id="legend"></div>
   <div class="tiles3" id="tiles3"></div>
   <div class="switch-row" id="sampleRow" hidden><button class="tog" id="sampleTog" role="switch" aria-checked="false" aria-label="Preview with sample progress"></button><span>Preview with sample progress <b style="color:var(--ink)">(made up, for judging the design; goes away after 7 scored days)</b></span></div>
   <div class="eyebrow" style="margin-top:16px">Verifiable record</div>
   <div class="small sub" id="recordNote"></div>
   <div class="history" id="history"></div>
   <details class="tableview"><summary>Show the journey as a table</summary><div id="journeyTable"></div></details>
  </section>

  <section class="card static-sum" id="staticSummary" aria-labelledby="staticSummaryH">__STATIC__</section>
  <div class="tiles4" id="tiles4"></div>
  <div class="card pair" id="warmCard" hidden><div class="eyebrow">Warm paths</div><div class="tiny sub" id="warmSub" style="margin-bottom:4px"></div><div id="warm"></div></div>
  <div class="card pair" id="unlocksCard"><div class="eyebrow">Biggest unlocks</div><div id="unlocks"></div></div>

  <nav class="views-nav" aria-label="Views"><div class="hscroll"><div class="seg" id="viewSeg" role="tablist" aria-label="Views"></div></div></nav>
  <section class="view on" id="v-level" role="tabpanel" aria-labelledby="tab-level">__LEVELUP__</section>
  <section class="view" id="v-orgs" role="tabpanel"></section>
  <section class="view" id="v-top" role="tabpanel"></section>
  <section class="view" id="v-moves" role="tabpanel"></section>
  <section class="view" id="v-roles" role="tabpanel"></section>
  <section class="view" id="v-swot" role="tabpanel"></section>
  <section class="view" id="v-plan" role="tabpanel"></section>
  <section class="view" id="v-evidence" role="tabpanel"></section>
  <section class="view" id="v-market" role="tabpanel"></section>
  <p class="tiny sub" style="margin:28px 4px 0">How scores work: seven factors, each 0 to 5 from cited evidence, weighted into a fit score out of 100, then turned into chance bands. A separate sceptical reviewer must agree with every score above 2. The projection applies each action on its target date, weighted by its chance of working, with caps so it can't overpromise; a role with an eligibility blocker you can't clear never gains eligibility. Bands are judgement, not statistics. Drafts only: the engine never applies, sends, posts or changes accounts. Last scored <span id="builtAt"></span>.</p>
 </main>

 <aside class="detail" id="detail" aria-label="Details">
  <div class="sheet-grip"></div>
  <div class="card" id="detailCard"></div>
 </aside>
</div>

<div class="bottombar" id="bottombar"><div class="bb-text"><b id="bbMain"></b><span id="bbSub"></span></div><button class="btn primary" id="fab">What if</button></div>
<div class="scrim" id="scrim"></div>
<div class="modal" id="modal" role="dialog" aria-modal="true" aria-label="Share progress"><div class="panel">
 <div class="d-head"><h3>Share your progress</h3><button class="close" id="modalClose" aria-label="Close">✕</button></div>
 <div class="share-card" id="shareCard"></div>
 <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center"><button class="btn primary" id="saveImg">Save as image</button><span class="small sub">No names of organisations or people are included.</span></div>
</div></div>
<div class="tip" id="tip" role="status"></div>
"""

JS_CORE = r"""
(function(){
"use strict";
const D = JSON.parse(document.getElementById("data").textContent);
const W = D.weights, CAPS = D.caps, DIMS = D.dims, TW = W.reduce((a, b) => a + b, 0) || 1;
const BANDS = ["Very low","Low","Moderate","Good","Strong"];
const THRESH = [0, 40, 55, 70, 85, 100];
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = s => document.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const tOf = iso => Date.parse(iso + "T00:00:00");
const fmtDate = iso => new Date(tOf(iso)).toLocaleDateString("en-AU", {day:"numeric", month:"short", year:"numeric"});
const fmtT = t => new Date(t).toLocaleDateString("en-AU", {day:"numeric", month:"short", year:"numeric"});
const shortDate = iso => new Date(tOf(iso)).toLocaleDateString("en-AU", {day:"numeric", month:"short"});
const r1 = v => Math.round(v * 10) / 10;
const isDark = () => document.documentElement.dataset.theme === "dark";
const orgColour = g => D.orgs[g] ? (isDark() ? D.orgs[g].cd : D.orgs[g].c) : "var(--line)";
const motionOK = () => !reduce && document.visibilityState === "visible";
const plural = (n, one, many) => n + " " + (n === 1 ? one : (many || one + "s"));
const stName = s => s === "doing" ? "In progress" : s === "later" ? "Parked for later" : s === "done" ? "Done" : s === "dropped" ? "Dropped" : "To do";
const cap1 = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
// The made-up sample progress is a design preview: reachable only with ?preview=1 in the address.
const PREVIEW = typeof location !== "undefined" && /[?&]preview=1(&|$)/.test(location.search);

// Mark an element as entering so its CSS animation runs, then always clear it,
// so a paused or skipped animation can never leave content hidden.
function enter(node, ms){ if (!node) return; node.classList.remove("enter"); void node.offsetWidth; node.classList.add("enter"); setTimeout(() => node.classList.remove("enter"), ms || 1300); }

// ---------- scoring and projection (mirrors method/RUBRIC.md and project() in build_dashboard.py) ----------
const roleById = {}; D.roles.forEach(r => roleById[r.id] = r);
const fitOf = s => r1(s.reduce((t, v, i) => t + v / 5 * W[i], 0) * 100 / TW);
const bandIdx = v => v >= 85 ? 4 : v >= 70 ? 3 : v >= 55 ? 2 : v >= 40 ? 1 : 0;
const clampBand = i => BANDS[Math.max(0, Math.min(4, i))];
function interviewBand(fit, s, hrl){ let i = bandIdx(fit); if (s[2] >= 4) i++; if (hrl) i--; return clampBand(i); }
function offerBand(fit, s, hrl){ let i = fit >= 85 ? 3 : fit >= 70 ? 2 : fit >= 55 ? 1 : 0; if (hrl) i--; if (s[2] <= 1) i = Math.min(i, 1); return clampBand(i); }
function inScope(r, sc){
  const ok = (list, v) => !(list && list.length) || list.indexOf(v) >= 0;
  return ok(sc.orgs, r.org) && ok(sc.families, r.family) && ok(sc.location_classes, r.lc) && ok(sc.role_ids, r.id);
}
const hardBlock = (r, k) => k === 5 && r.hard;              // a blocker the plan can't clear keeps eligibility at 0
const live = a => a.status === "todo" || a.status === "doing";
// Parked (status later): off by default, and in the projection, the next level and the quests only while switched on.
const switchable = a => live(a) || a.status === "later";
const enabled = new Set(D.actions.filter(live).map(a => a.id));
const TODAY = D.meta.run_date;
// Apply a list of actions (in target-date order). sure: one action id treated as certain to work.
// Mirrors walk() in scripts/_levels.py.
function walkL(r, acts, mode, sure){
  const base = r.s.slice(), s = r.s.slice();
  const pts = [{d: TODAY, v: r.fit}];
  acts.forEach(a => {
    if (!switchable(a)) return;
    const p = (mode === "best" || a.id === sure) ? 1 : a.p;
    a.effects.forEach(e => {
      if (!inScope(r, e.scope || {})) return;
      const k = DIMS.indexOf(e.dimension);
      if (k < 0 || hardBlock(r, k)) return;
      const cur = s[k];
      let nw = ("delta" in e) ? cur + e.delta : Math.max(cur, e.set_at_least);
      nw = Math.min(5, nw, base[k] + CAPS[k]);
      if (nw > cur) s[k] = cur + p * (nw - cur);
    });
    pts.push({d: a.date < TODAY ? TODAY : a.date, v: fitOf(s)});
  });
  return {pts, end: fitOf(s), scores: s};
}
function project(r, mode, on){
  on = on || enabled;
  const w = walkL(r, D.actions.filter(a => on.has(a.id)), mode);   // D.actions is already in target-date order
  w.pts.push({d: D.meta.end, v: w.end});
  return w;
}
// The best fit across roles after the same actions (the level follows it, so any role can carry it).
// Ties go to the role listed first, so today's best wins a tie. pts: the best fit at each step.
// Mirrors best_of() in scripts/_levels.py.
function bestOf(rs, acts, mode, sure){
  if (!rs.length) return null;
  let best = null, pts = null;
  rs.forEach(r => { const w = walkL(r, acts, mode, sure);
    if (!best || w.end > best.end) best = {end: w.end, r, scores: w.scores};
    pts = pts ? pts.map((p, i) => ({d: p.d, v: Math.max(p.v, w.pts[i].v)})) : w.pts; });
  best.pts = pts;
  return best;
}

// ---------- state + per-refresh cache ----------
const state = {org: "best", mode: "today", sample: false, view: "level", stack: []};
let P = {};                                                // role id -> {exp, best}
let LV = null;                                             // the journey's next level, quests and Do next order (see lv())
let JPC = {};                                              // journey -> its projection (see jp())
function recompute(){ P = {}; LV = null; JPC = {}; D.roles.forEach(r => P[r.id] = {exp: project(r, "exp"), best: project(r, "best")}); }
function fitM(r, mode){ mode = mode || state.mode; return mode === "today" ? r.fit : P[r.id][mode].end; }
function scoresM(r, mode){ mode = mode || state.mode; return mode === "today" ? r.s : P[r.id][mode].scores; }
function ibM(r, mode){ mode = mode || state.mode; return mode === "today" ? r.ib : interviewBand(fitM(r, mode), scoresM(r, mode), r.hrl); }
function obM(r, mode){ mode = mode || state.mode; return mode === "today" ? r.ob : offerBand(fitM(r, mode), scoresM(r, mode), r.hrl); }
const MODES = [["today","Today"],["exp","Plan expected"],["best","Plan best case"]];
const modeName = () => ({today:"today", exp:"if you follow the plan, by " + shortDate(D.meta.end), best:"if every action lands, by " + shortDate(D.meta.end)})[state.mode];
// Today's best role on a journey ("best" for every role, or an organisation key; the selector's by default).
function headlineRole(org){
  org = org || state.org;
  if (org === "best") return D.roles[0];
  return roleById[D.orgs[org].best] || D.roles.find(r => r.g === org);
}
// The roles the journey follows, today's best first: every role, or the selected organisation's.
function journeyRoles(org){
  org = org || state.org;
  const h = headlineRole(org);
  return org === "best" ? D.roles : [h].concat(D.roles.filter(r => r.g === org && r !== h));
}
// The journey's projection under the switches: at each step the best fit across its roles, the same yardstick
// as the level (bestOf), so the chart, its tiles, the phone bar, the share card, What if and Level up give one
// answer. exp.r and best.r: the role holding each end (a tie keeps today's order, so today's best wins it).
function planProj(rs, on){
  on = on || enabled;
  const acts = D.actions.filter(a => on.has(a.id));
  const end = w => ({end: w.end, scores: w.scores, r: w.r, pts: w.pts.concat([{d: D.meta.end, v: w.end}])});
  return {exp: end(bestOf(rs, acts, "exp")), best: end(bestOf(rs, acts, "best"))};
}
function jp(org){ org = org || state.org; if (!JPC[org]) JPC[org] = planProj(journeyRoles(org)); return JPC[org]; }
function crossDate(pts, threshold){
  for (let i = 0; i < pts.length; i++) if (pts[i].v >= threshold) return pts[i].d;   // an action lands on its target date
  return null;
}

// ---------- helpers ----------
function pill(band){ return `<span class="pill pb${BANDS.indexOf(band)}">${esc(band)}</span>`; }
function countTo(node, to, dur){
  const from = parseFloat(node.dataset.v || "0"); node.dataset.v = to;
  node.textContent = Math.round(to);                          // final state first
  if (!motionOK() || Math.round(from) === Math.round(to)) return;
  const t0 = performance.now(), d = dur || 650;
  const step = now => { const k = Math.min(1, (now - t0) / d), e = 1 - Math.pow(1 - k, 3);
    node.textContent = Math.round(from + (to - from) * e); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
  setTimeout(() => { node.textContent = Math.round(to); }, d + 250);
}
const tip = $("#tip");
function showTip(e, nodes){ tip.textContent = ""; nodes.forEach(n => tip.appendChild(n)); tip.style.display = "block"; placeTip(e); }
function placeTip(e){ let x = e.clientX + 14, y = e.clientY + 14;
  if (x + tip.offsetWidth > innerWidth - 8) x = e.clientX - tip.offsetWidth - 14;
  if (y + tip.offsetHeight > innerHeight - 8) y = e.clientY - tip.offsetHeight - 14;
  tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px"; }
const hideTip = () => tip.style.display = "none";
function el(tag, cls, text){ const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
function svgEl(tag, attrs){ const n = document.createElementNS("http://www.w3.org/2000/svg", tag); Object.keys(attrs).forEach(k => n.setAttribute(k, attrs[k])); return n; }
function bindTips(root){ root.querySelectorAll("[data-tip]").forEach(b => { b.addEventListener("pointermove", e => showTip(e, [el("div", "", b.dataset.tip)])); b.addEventListener("pointerleave", hideTip);
  b.addEventListener("focus", () => { const r = b.getBoundingClientRect(); showTip({clientX: r.left, clientY: r.bottom}, [el("div", "", b.dataset.tip)]); }); b.addEventListener("blur", hideTip); }); }
function onEnter(n, go){ n.addEventListener("click", go); n.addEventListener("keydown", e => { if (e.key === "Enter") go(); }); }

// ---------- flight strip, best chance, level ----------
function renderTopline(){
  const r = headlineRole(), exp = jp().exp;
  const sp = state.sample ? sampleProgress(r) : [];
  const last = sp.length ? sp[sp.length - 1] : {t: tOf(TODAY), v: r.fit};
  const day = Math.round((last.t - T0) / 864e5) + 1;
  const bi = bandIdx(last.v);
  const nextT = bi < 4 ? THRESH[bi + 1] : null;
  const nextDate = nextT != null ? crossDate(exp.pts, nextT) : null;
  $("#strip").innerHTML = `<span>Departed<b>${esc(fmtDate(D.meta.baseline))}</b></span><span>Day<b class="num">${day}</b></span>
    <span>Altitude<b class="num">${Math.round(last.v)}</b></span><span>Flight level<b>${esc(BANDS[bi])}</b></span>
    <span>Next level (${esc(nextT != null ? BANDS[bi + 1] : "top")})<b>${nextDate ? esc(fmtDate(nextDate)) : "not on the current plan"}</b></span>`;
  // best chance (mode aware)
  const focus = journeyRoles().reduce((a, b) => fitM(b) > fitM(a) ? b : a);   // the role the journey's projection follows
  $("#bestLabel").textContent = (state.org === "best" ? "Best match " : D.orgs[focus.g].name + ", best match ") + modeName();
  countTo($("#bestNum"), fitM(focus));
  $("#bestPills").innerHTML = `Interview ${pill(ibM(focus))} Offer ${pill(obM(focus))}`;
  $("#bestRole").textContent = `${focus.on}: ${focus.title}`;
  // level (today, actual): the next level and what gets you there
  $("#level").innerHTML = levelCardHTML(lv().nl);
  $("#level").querySelectorAll("[data-go-level]").forEach(b => b.addEventListener("click", goLevel));
  enter($("#level .lvl-pop"), 900);
}
"""

JS_CHART = r"""
// ---------- journey chart ----------
// The chart's coordinate space matches its real pixel width, so 11 to 12px labels stay 11 to 12px.
// The measured record runs from Day 1 to today; the three paths run from today to the end date.
// On a phone (SMALL) the band labels shrink to their names and the end labels move inside the plot.
let CW = 760, CH = 330, PL = 40, PR = 118, IW = 602, IH = 284, SMALL = false;
const PT = 16, PB = 30;
function layoutChart(){
  CW = Math.max(260, Math.round($("#chartWrap").clientWidth) || 760);
  SMALL = CW < 560;
  CH = SMALL ? 300 : 330; PL = SMALL ? 60 : 82; PR = SMALL ? 6 : 118;
  IW = CW - PL - PR; IH = CH - PT - PB;
}
const HALO = 'stroke="var(--card)" stroke-width="4" stroke-linejoin="round" paint-order="stroke"';
const T0 = tOf(D.meta.baseline), TN = tOf(TODAY), T1 = tOf(D.meta.end);
const xT = t => PL + (t - T0) / (T1 - T0) * IW;
const xOf = iso => xT(tOf(iso));
const yOf = v => PT + IH - v / 100 * IH;
const N = 64; const SAMPLE_T = Array.from({length: N}, (_, i) => TN + i * (T1 - TN) / (N - 1));
function valueAt(pts, t){
  if (t <= tOf(pts[0].d)) return pts[0].v;
  for (let i = 1; i < pts.length; i++){
    const ta = tOf(pts[i-1].d), tb = tOf(pts[i].d);
    if (t <= tb) return tb === ta ? pts[i].v : pts[i-1].v + (pts[i].v - pts[i-1].v) * (t - ta) / (tb - ta);
  }
  return pts[pts.length - 1].v;
}
const sampleSeries = pts => SAMPLE_T.map(t => valueAt(pts, t));
const pathFrom = vals => vals.map((v, i) => (i ? "L" : "M") + xT(SAMPLE_T[i]).toFixed(1) + "," + yOf(v).toFixed(1)).join(" ");
const pathPts = list => list.map((p, i) => (i ? "L" : "M") + xT(p.t).toFixed(1) + "," + yOf(p.v).toFixed(1)).join(" ");
function sampleProgress(r){
  const exp = jp().exp.pts, out = [], base = r.fit; let seed = 7;
  const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
  for (let w = 1; w <= 12; w++){ const t = TN + w * 7 * 864e5; if (t > T1) break;
    out.push({t, v: r1(Math.max(base, base + (valueAt(exp, t) - base) * 0.9 + (rnd() - 0.5) * 1.6))}); }
  return out;
}
function history(r){
  return D.runs.map(rn => ({t: tOf(rn.date), v: rn.date === TODAY ? r.fit : state.org === "best" ? rn.top : rn.orgs[state.org]}))
    .filter(p => p.v != null);
}
let lastVals = null, chartBuilt = false, chartState = null;
function buildChartFrame(){
  layoutChart();
  const zones = [[0,40,"Very low","0 to 39"],[40,55,"Low","40 to 54"],[55,70,"Moderate","55 to 69"],[70,85,"Good","70 to 84"],[85,100,"Strong","85 to 100"]];
  let z = "", grid = "";
  zones.forEach((zz, i) => {
    z += `<rect x="${PL}" y="${yOf(zz[1])}" width="${IW}" height="${yOf(zz[0]) - yOf(zz[1])}" fill="var(--z${i % 2})"/>`;
    const mid = (yOf(zz[0]) + yOf(zz[1])) / 2;             // flight levels sit in the left gutter
    if (SMALL) z += `<text class="zone-label" x="${PL - 6}" y="${mid + 4}" text-anchor="end" font-size="11">${zz[2]}</text>`;
    else z += `<text class="zone-label" x="${PL - 16}" y="${mid - 1}" text-anchor="end">${zz[2]}</text><text class="axis" x="${PL - 16}" y="${mid + 12}" text-anchor="end">${zz[3]}</text>`;
  });
  const d0 = new Date(T0), months = [];
  for (let m = 0; m < 60; m++){ const d = new Date(d0.getFullYear(), d0.getMonth() + m, 1), t = d.getTime(); if (t > T1) break; if (t >= T0) months.push(d); }
  const every = Math.max(1, Math.ceil(months.length / (SMALL ? 4 : 7)));
  months.forEach((d, i) => { if (i % every) return; const x = xT(d.getTime());
    grid += `<line class="gridline" x1="${x}" x2="${x}" y1="${PT}" y2="${PT + IH}"/><text class="axis" x="${x}" y="${CH - 8}" text-anchor="middle">${d.toLocaleDateString("en-AU",{month:"short"})}</text>`; });
  const xn = xT(TN);
  if (TN > T0) grid += `<line x1="${xn}" x2="${xn}" y1="${PT}" y2="${PT + IH}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="3 3"/><text x="${xn}" y="${CH - 8}" text-anchor="middle" font-size="11" font-weight="650" fill="var(--accent)" ${HALO}>Today</text>`;
  $("#chartWrap").innerHTML = `<svg viewBox="0 0 ${CW} ${CH}" role="img" aria-label="Journey chart: fit score over time, the measured record so far, and the expected, best case and do nothing paths">
    <defs><clipPath id="clipReveal"><rect class="reveal" x="${PL - 10}" y="0" width="${IW + PR + 10}" height="${CH}"/></clipPath></defs>
    ${z}${grid}
    <line x1="${PL}" x2="${PL + IW}" y1="${yOf(70)}" y2="${yOf(70)}" stroke="var(--ok)" stroke-width="1.5" stroke-dasharray="5 4"/>
    ${SMALL ? `<text x="${PL + 6}" y="${yOf(70) - 6}" font-size="11" font-weight="750" fill="var(--ok)" ${HALO}>Offer zone, fit 70 and up</text>` : ""}
    <g clip-path="url(#clipReveal)">
      <path id="pNone" class="series" stroke="var(--stop)" stroke-dasharray="2 4"/>
      <path id="pBest" class="series" stroke-dasharray="7 5"/>
      <path id="pExp" class="series"/>
      <path id="pSample" class="series" stroke="var(--ink)" stroke-dasharray="4 3" visibility="hidden"/>
      <g id="wps"></g><g id="actual"></g>
    </g>
    <g id="labels"></g>
    <line id="cross" class="cross" y1="${PT}" y2="${PT + IH}" visibility="hidden"/>
    <rect class="hit" id="hit" x="${PL}" y="${PT}" width="${IW}" height="${IH}"/>
  </svg>`;
  $("#hit").addEventListener("pointermove", onChartMove);
  $("#hit").addEventListener("pointerleave", () => { hideTip(); $("#cross").setAttribute("visibility", "hidden"); });
  chartBuilt = true;
}
// Phone end labels sit inside the plot, right aligned and centred on their own line (the baseline 4px below
// it), so each number reads beside the line it names. When two would overlap, the lower one moves down, at
// least 13px apart (like the desktop labels), so equal values, as on every first run, read as three separate
// labels, and the stack stays between top and bottom of the plot.
function phoneEndLabels(ends, top, bottom){
  const GAP = 13, out = ends.map((e, i) => [e[0], e[1] + 4, e[1], i]);
  const order = out.slice().sort((a, b) => a[2] - b[2] || a[3] - b[3]);   // by line height, ties keep best, expected, do nothing
  order.forEach((e, i) => { e[1] = Math.max(e[1], top + i * GAP); if (i) e[1] = Math.max(e[1], order[i - 1][1] + GAP); });
  for (let i = order.length - 1; i >= 0; i--) order[i][1] = Math.min(order[i][1], i === order.length - 1 ? bottom : order[i + 1][1] - GAP);
  return out.map(e => [e[0], e[1]]);
}
function drawChart(){
  if (!chartBuilt) buildChartFrame();
  const r = headlineRole(), J = jp(), exp = J.exp, best = J.best, c = orgColour(exp.r.g);
  const vals = {exp: sampleSeries(exp.pts), best: sampleSeries(best.pts), none: SAMPLE_T.map(() => r.fit)};
  $("#pExp").setAttribute("stroke", c); $("#pBest").setAttribute("stroke", c);
  const ids = {exp: "#pExp", best: "#pBest", none: "#pNone"};
  const apply = (from, k) => Object.keys(ids).forEach(key => $(ids[key]).setAttribute("d", pathFrom(from[key].map((a, i) => a + (vals[key][i] - a) * k))));
  const from = lastVals; lastVals = vals;
  apply(vals, 1);                                               // final state first
  if (from && motionOK()){
    const t0 = performance.now();
    const step = now => { const k = Math.min(1, (now - t0) / 380), e = 1 - Math.pow(1 - k, 3); apply(from, e); if (k < 1) requestAnimationFrame(step); };
    apply(from, 0); requestAnimationFrame(step);
    setTimeout(() => apply(vals, 1), 700);
  }
  // waypoints
  const g = $("#wps"); g.textContent = "";
  const dz = SMALL ? 5 : 7;
  D.actions.forEach(a => {
    if (!enabled.has(a.id) || !switchable(a)) return;
    const when = a.date < TODAY ? TODAY : a.date;
    const x = xOf(when), y = yOf(valueAt(exp.pts, tOf(when)));
    const fill = a.status === "doing" ? c : "var(--card)";
    const s = svgEl("path", {d: `M${x},${y - dz} L${x + dz},${y} L${x},${y + dz} L${x - dz},${y} Z`, fill, stroke: c, "stroke-width": SMALL ? 1.6 : 2, class: "wp", tabindex: 0});
    s.addEventListener("pointermove", e => { e.stopPropagation(); showTip(e, [el("div", "tv", a.title), el("div", "tn", (a.dated ? "Waypoint, target " + fmtDate(a.date) : "No target date yet, counted at the end") + ", " + Math.round(a.p * 100) + "% chance it works")]); });
    s.addEventListener("pointerleave", hideTip);
    s.addEventListener("click", () => openDetail({type: "action", id: a.id}, true));
    g.appendChild(s);
  });
  // the measured record, the sample, the aircraft
  const act = $("#actual"); act.textContent = "";
  const hist = history(r);
  if (hist.length > 1) act.appendChild(svgEl("path", {d: pathPts(hist), class: "series", stroke: "var(--ink)"}));
  const samp = state.sample ? sampleProgress(r) : [];
  const sp = $("#pSample");
  if (samp.length){ sp.setAttribute("d", pathPts([hist[hist.length - 1]].concat(samp))); sp.setAttribute("visibility", "visible"); }
  else sp.setAttribute("visibility", "hidden");
  hist.forEach(p => act.appendChild(svgEl("circle", {cx: xT(p.t), cy: yOf(p.v), r: 5, fill: "var(--ink)", stroke: "var(--card)", "stroke-width": 2})));
  const today = samp.length ? samp[samp.length - 1] : hist[hist.length - 1];
  const plane = svgEl("g", {transform: `translate(${xT(today.t)},${yOf(today.v)})`});
  plane.appendChild(svgEl("circle", {r: 12, fill: "var(--accent-soft)", stroke: "var(--accent)", "stroke-width": 1.5}));
  plane.appendChild(svgEl("path", {d: "M-8,1 L6,-1 L9,0 L6,1 L-8,-1 Z M-2,0 L-5,-7 L-2.5,-7 L3,0 L-2.5,7 L-5,7 Z", fill: "var(--accent)", transform: "rotate(-14)"}));
  act.appendChild(plane);
  // labels: the departure, and the three end labels
  const lab = $("#labels"); lab.textContent = "";
  const txt = (x, y, s, bold, fill, anchor) => { const n = svgEl("text", {x, y, "font-size": SMALL ? 11 : 12, "font-weight": bold ? 750 : 550, fill: fill || "var(--ink)", "text-anchor": anchor || "start"});
    n.setAttribute("stroke", "var(--card)"); n.setAttribute("stroke-width", 4); n.setAttribute("stroke-linejoin", "round"); n.setAttribute("paint-order", "stroke");
    n.textContent = s; lab.appendChild(n); };
  hist.forEach((p, i) => {                                     // level-up moments (and honest level-downs)
    if (!i) return; const a = bandIdx(hist[i - 1].v), b = bandIdx(p.v); if (a === b) return;
    const x = xT(p.t), y = yOf(p.v), up = b > a;
    act.appendChild(svgEl("path", {d: up ? `M${x},${y - 18} l5.5,7.5 h-11 Z` : `M${x},${y + 18} l5.5,-7.5 h-11 Z`, fill: up ? "var(--ok)" : "var(--line)"}));
    if (up && !SMALL) txt(x - 9, y - 12, "Level " + (b + 1), true, "var(--ok)", "end");
  });
  const d1 = hist.length ? hist[0].v : r.fit;
  txt(xT(hist.length ? hist[0].t : T0) + 10, Math.min(PT + IH - 6, yOf(d1) + 24), "Day 1: " + BANDS[bandIdx(d1)] + ", fit " + Math.round(d1), true);
  // end labels: outside the plot on wide screens, inside it (right aligned, on each line) on a phone
  const ends = [[Math.round(best.end) + " Best case", yOf(best.end)], [Math.round(exp.end) + " Expected", yOf(exp.end)], [Math.round(r.fit) + " Do nothing", yOf(r.fit)]];
  if (SMALL){                                                  // each label ends in a short key drawn like its line
    const keys = [[c, "7 5"], [c, "none"], ["var(--stop)", "2 4"]];
    phoneEndLabels(ends, PT + 12, PT + IH - 4).forEach((e, i) => {
      lab.appendChild(svgEl("line", {x1: PL + IW - 16, x2: PL + IW - 2, y1: e[1] - 4, y2: e[1] - 4, stroke: keys[i][0],
        "stroke-width": 2, "stroke-dasharray": keys[i][1], "stroke-linecap": "round", class: "end-key"}));
      txt(PL + IW - 20, e[1], e[0], false, "var(--sub)", "end");
    });
  } else {                                                     // the offer zone label joins the end labels, so none overlap
    const items = ends.map(e => ({y: e[1] + 4, h: 15, draw: y => txt(PL + IW + 8, y, e[0], false, "var(--sub)")}));
    items.push({y: yOf(70) - 4, h: 29, draw: y => { txt(PL + IW + 8, y, "Offer zone", true, "var(--ok)"); txt(PL + IW + 8, y + 14, "fit 70 and up", false, "var(--sub)"); }});
    items.sort((a, b) => a.y - b.y);
    for (let i = 1; i < items.length; i++) items[i].y = Math.max(items[i].y, items[i-1].y + items[i-1].h);
    items.forEach(it => it.draw(it.y));
  }
  $("#legend").innerHTML = `<span style="color:var(--ink)"><i class="lk"></i><span class="sub">Measured, one dot per scored day${state.sample ? ", sample shown dashed" : ""}</span></span>
    <span style="color:${c}"><i class="lk"></i><span class="sub">Expected if you follow the plan</span></span>
    <span style="color:${c}"><i class="lk" style="border-top-style:dashed"></i><span class="sub">Best case, every action lands</span></span>
    <span style="color:var(--stop)"><i class="lk" style="border-top-style:dotted"></i><span class="sub">Do nothing</span></span>
    <span><svg width="12" height="12" viewBox="-6 -6 12 12" aria-hidden="true"><path d="M0,-5 L5,0 L0,5 L-5,0 Z" fill="var(--card)" stroke="${c}" stroke-width="1.6"/></svg><span class="sub">Plan action</span></span>`;
  const rows = hist.slice(0, -1).map(p => `<tr><td>${fmtT(p.t)}</td><td class="num">${Math.round(p.v)}</td><td></td><td></td><td></td></tr>`).join("") +
    exp.pts.map((p, i) => `<tr><td>${fmtDate(p.d)}${i === 0 ? " (today)" : ""}</td><td class="num">${i === 0 ? Math.round(r.fit) : ""}</td><td class="num">${Math.round(p.v)}</td><td class="num">${Math.round(best.pts[i].v)}</td><td class="num">${Math.round(r.fit)}</td></tr>`).join("");
  $("#journeyTable").innerHTML = `<div class="tscroll"><table><tr><th>Date</th><th>Measured</th><th>Expected</th><th>Best case</th><th>Do nothing</th></tr>${rows}</table></div>`;
  $("#tiles3").innerHTML = [["Expected by " + shortDate(D.meta.end), exp.end, interviewBand(exp.end, exp.scores, exp.r.hrl)],
    ["If every action lands", best.end, interviewBand(best.end, best.scores, best.r.hrl)], ["If you do nothing", r.fit, r.ib]]
    .map(t => `<div class="tile3"><div class="l">${esc(t[0])}</div><div class="v num" data-to="${t[1]}">${Math.round(t[1])}</div>${pill(t[2])} <span class="tiny sub">interview</span></div>`).join("");
  $("#tiles3").querySelectorAll("[data-to]").forEach(n => countTo(n, +n.dataset.to));
  chartState = {r, c, exp, best, hist};
}
function onChartMove(e){
  if (!chartState) return;
  const rect = $("#chartWrap svg").getBoundingClientRect(), sx = (e.clientX - rect.left) * (CW / rect.width);
  const t = Math.max(T0, Math.min(T1, T0 + (sx - PL) / IW * (T1 - T0)));
  const {r, c, exp, best, hist} = chartState, cr = $("#cross");
  const row = (val, name, colour, dash) => { const d = el("div", "tip-row"), k = el("i", "lk"); k.style.color = colour; if (dash) k.style.borderTopStyle = dash; d.appendChild(k); d.appendChild(el("span", "tv", String(Math.round(val)))); d.appendChild(el("span", "tn", name)); return d; };
  if (t < TN && hist.length){
    const p = hist.reduce((a, b) => Math.abs(b.t - t) < Math.abs(a.t - t) ? b : a, hist[0]);
    cr.setAttribute("x1", xT(p.t)); cr.setAttribute("x2", xT(p.t)); cr.setAttribute("visibility", "visible");
    const i = hist.indexOf(p), b = bandIdx(p.v), a = i > 0 ? bandIdx(hist[i - 1].v) : b;
    showTip(e, [el("div", "tn", fmtT(p.t)), row(p.v, "measured", "var(--ink)"), el("div", "tn", "Level " + (b + 1) + ", " + BANDS[b] + (b > a ? ", level up from " + BANDS[a] : b < a ? ", down from " + BANDS[a] : ""))]);
    return;
  }
  const ts = SAMPLE_T[Math.max(0, Math.min(N - 1, Math.round((t - TN) / ((T1 - TN) / (N - 1)))))];
  cr.setAttribute("x1", xT(ts)); cr.setAttribute("x2", xT(ts)); cr.setAttribute("visibility", "visible");
  showTip(e, [el("div", "tn", fmtT(ts)), row(valueAt(exp.pts, ts), "expected", c), row(valueAt(best.pts, ts), "best case", c, "dashed"), row(r.fit, "do nothing", "var(--stop)", "dotted")]);
}
"""

JS_HOME = r"""
// ---------- scoreboard tiles, Do next and Biggest unlocks ----------
function renderTiles4(){
  const J = D.roles.filter(r => r.judged), fits = J.map(r => fitM(r)).sort((a, b) => b - a);   // a role not judged yet has no real fit
  const top5 = fits.length ? fits.slice(0, 5).reduce((a, b) => a + b, 0) / Math.min(5, fits.length) : 0;
  const lowPlus = J.filter(r => BANDS.indexOf(ibM(r)) >= 1).length;
  const open = J.filter(r => !r.blocked).length, of = D.roles.length > J.length ? `, of ${J.length} judged` : "";
  const tiles = [["Best role fit", fits[0] || 0], ["Average of your top 5", top5], ["Roles at a low interview chance or better" + of, lowPlus], ["Roles open to you" + of, open]];
  $("#tiles4").innerHTML = tiles.map(t => `<div class="tile"><div class="v num" data-to="${t[1]}">${Math.round(t[1])}</div><div class="l">${esc(t[0])}</div></div>`).join("");
  $("#tiles4").querySelectorAll("[data-to]").forEach(n => countTo(n, +n.dataset.to));
}
const byWhen = a => a.dated ? "by " + shortDate(a.date) : "no target date yet";
// Do next and Biggest unlocks live in the right pane on wide screens (its home state), and on narrower
// screens Do next sits in the journey card under the headline status, so they are rendered as strings.
// Do next is the top of the one ranked list (the quests in the same order): one points number per action.
const DO_NEXT = 4;
function doNextHTML(){ const L = lv(); return doNextRows(L.up, L.nl, DO_NEXT); }
function unlocksHTML(){
  return D.gaps.slice(0, 4).map(x => `<div class="dn" tabindex="0" data-moves="1"><div style="flex:1;min-width:0"><div class="dn-t">${esc(x.title)}</div><div class="tiny sub">${plural(x.roles, "role")}</div></div><div class="dn-p">+${x.points}</div></div>`).join("") +
    `<button class="linkbtn" data-see-moves="1" style="margin-top:8px">See everything that moves you ›</button>`;
}
// Warm paths (campaign/warm-paths.json): how far each contact at each organisation has come. Progress only: no score
// reads it. One strip per organisation, filled up to the furthest stage anyone there has reached; the words say it too.
const warmSub = () => "From followed to would refer. Progress only: it changes no score.";
function warmBar(n){ let s = ""; for (let i = 0; i < 5; i++) s += `<i${i <= n ? ' class="on"' : ""}></i>`; return `<span class="wp-bar" aria-hidden="true">${s}</span>`; }
function warmRow(o){
  const W = D.warm, open = D.orgs[o.g] ? ` tabindex="0" data-org-open="${esc(o.g)}"` : "";
  const counts = o.counts.map((n, i) => n ? n + " " + W.stages[i].toLowerCase() : "").filter(Boolean).join(", ");
  return `<div class="wp"${open}><div class="wp-h"><span class="wp-n">${esc(o.name)}</span>${o.people ? `<span class="wp-s"><span class="sr-only">furthest stage: </span>${esc(W.stages[o.furthest])}</span>` : '<span class="wp-s none">No one yet</span>'}</div>${warmBar(o.furthest)}${o.people ? `<div class="tiny sub">${o.people === 1 ? "1 person" : esc(plural(o.people, "person", "people") + ": " + counts)}</div>` : ""}</div>`;
}
function warmHTML(){
  const W = D.warm; if (!W || !W.orgs.length) return "";
  return `<div>${W.orgs.map(warmRow).join("")}</div>` + (W.orgs.some(o => o.people) ? "" : '<div class="tiny sub" style="margin-top:6px">Tell your agent who you know at each organisation and how far you have got.</div>');
}
function warmDetail(L){
  const W = D.warm, mine = W ? W.orgs.filter(o => L.members.includes(o.id)) : [];
  if (!mine.length) return "";
  return `<div class="eyebrow" style="margin-top:16px">Warm paths</div><div class="tiny sub">${esc(W.note)}</div>` + mine.map(o => {
    const cs = W.contacts.filter(c => c.org === o.id);
    return `<div class="wp-h" style="margin-top:8px"><span class="small"${mine.length > 1 ? ' style="font-weight:600"' : ""}>${mine.length > 1 ? esc(o.name) : "Furthest stage"}</span><span class="wp-s${o.furthest >= 0 ? "" : " none"}">${o.furthest >= 0 ? esc(W.stages[o.furthest]) : "No one yet"}</span></div>` + warmBar(o.furthest) +
      (cs.map(c => `<div class="wp-c"><span class="tag">${esc(W.stages[c.stage])}</span> <span class="small">${esc(cap1(c.who))}${c.role ? ", " + esc(c.role) : ""}</span>${c.since || c.next ? `<div class="tiny sub">${c.since ? "Updated " + esc(shortDate(c.since)) : ""}${c.since && c.next ? " · " : ""}${c.next ? "Next: " + esc(c.next) : ""}</div>` : ""}</div>`).join("") || '<div class="tiny sub">Nobody tracked here yet.</div>');
  }).join("");
}
function goMoves(){ state.view = "moves"; renderViewSeg(); showView(); $(".views-nav").scrollIntoView({behavior: motionOK() ? "smooth" : "auto", block: "start"}); }
function bindHome(root){
  root.querySelectorAll(".dn[data-act]").forEach(n => onEnter(n, () => openDetail({type: "action", id: n.dataset.act}, true)));
  root.querySelectorAll("[data-moves],[data-see-moves]").forEach(n => onEnter(n, goMoves));
  root.querySelectorAll("[data-org-open]").forEach(n => onEnter(n, () => openDetail({type: "org", id: n.dataset.orgOpen}, true)));
}
function renderDoNext(){
  $("#doNext").innerHTML = `<div class="tiny sub" style="margin-bottom:4px">${esc(doNextSub(lv().nl))}</div>${doNextHTML()}`; $("#nextIn").hidden = false;
  $("#unlocks").innerHTML = unlocksHTML(); bindHome($("#nextIn")); bindHome($("#unlocksCard"));
  const warm = warmHTML(); $("#warm").innerHTML = warm; $("#warmCard").hidden = !warm;
  if (warm){ $("#warmSub").textContent = warmSub(); bindHome($("#warmCard")); }
  if (!narrow() && !state.stack.length) renderHome();
}
function renderHome(){
  const card = $("#detailCard"), warm = warmHTML();
  card.innerHTML = `<div class="d-body"><div class="eyebrow">Start here</div><h2 class="pane-h" style="margin:0">Do next</h2><div class="tiny sub" style="margin-bottom:4px">${esc(doNextSub(lv().nl))}</div><div>${doNextHTML()}</div>
    ${warm ? `<h2 class="pane-h" style="margin:18px 0 0">Warm paths</h2><div class="tiny sub" style="margin-bottom:4px">${esc(warmSub())}</div>${warm}` : ""}
    <h2 class="pane-h" style="margin:18px 0 0">Biggest unlocks</h2><div class="tiny sub" style="margin-bottom:4px">Fit points gained, added up across your top judged roles.</div><div>${unlocksHTML()}</div>
    <div class="tiny sub" style="margin-top:18px;padding-top:12px;border-top:1px solid var(--rule)">Tap any organisation, role, factor, action or piece of evidence to drill in here.</div></div>`;
  bindHome(card);
}

// ---------- rail ----------
// The rail keeps the Do next order the page opened with, so its rows never jump while you switch.
let RANK = {};
function renderSwitches(){
  const box = {now: $("#switchesNow"), later: $("#switchesLater"), done: $("#switchesDone")};
  Object.values(box).forEach(b => b.innerHTML = "");
  const groups = {now: [], later: [], done: []};
  D.actions.forEach(a => { if (groups[a.group]) groups[a.group].push(a); });
  const rank = a => a.id in RANK ? RANK[a.id] : 1e3;
  const byRank = (x, y) => (rank(x) - rank(y)) || (y.priority - x.priority) || (tOf(x.date) - tOf(y.date));
  groups.now.sort(byRank); groups.later.sort(byRank);
  groups.done.sort((x, y) => tOf(y.date) - tOf(x.date));
  const onIn = list => list.filter(a => enabled.has(a.id)).length;
  $("#nowCount").textContent = `${onIn(groups.now)} of ${groups.now.length} on`;
  $("#laterLabel").textContent = `Later (${groups.later.length}, ${onIn(groups.later)} on)`;
  $("#laterBox").hidden = !groups.later.length;
  $("#doneLabel").textContent = `Done (${groups.done.length})`;
  $("#doneBox").hidden = !groups.done.length;
  if (!groups.now.length) $("#switchesNow").innerHTML = '<div class="small sub" style="padding:10px 0">No open actions yet.</div>';
  ["now", "later", "done"].forEach(gk => groups[gk].forEach(a => {
    const row = el("div", "sw");
    if (gk === "done"){
      row.innerHTML = `<div class="sw-main"><div class="sw-title">${esc(a.title)}</div><div class="sw-meta">Done ${esc(shortDate(a.date))}</div></div><span class="done-tick" aria-label="Done">✓</span>`;
    } else {
      const on = enabled.has(a.id);
      // The only place the marginal number appears: what this action adds to your best role with everything else switched on.
      const w = new Set(enabled); w.add(a.id); const wo = new Set(enabled); wo.delete(a.id);
      const lift = r1(planProj(D.roles, w).exp.end - planProj(D.roles, wo).exp.end);   // on your best fit, as Level up counts it
      let lifted = 0; D.roles.forEach(r => { if (project(r, "exp", w).end - project(r, "exp", wo).end > 0.05) lifted++; });
      row.innerHTML = `<div class="sw-main"><div class="sw-title">${esc(a.title)}</div>
        <div class="sw-lift">${lift > 0 ? `<b>+${lift.toFixed(1)}</b> with everything else on${lifted ? `, lifts <b>${lifted}</b> ${lifted === 1 ? "role" : "roles"}` : ""}` : !a.effects.length ? "Protects credibility, no score change" : `Little extra with everything else on${lifted ? `, but lifts <b>${lifted}</b> ${lifted === 1 ? "role" : "roles"}` : ""}`}</div>
        <div class="sw-meta"><span class="status-dot ${esc(a.status)}"></span>${a.status === "doing" ? "In progress" : a.status === "later" ? "Parked for later" : "To do"} · ${esc(byWhen(a))}${a.stale ? ` · <span class="stale">No movement in ${a.stale} runs</span>` : ""}</div></div>
        <button class="tog" role="switch" aria-checked="${on}" aria-label="${esc(a.title)}"></button>`;
      row.querySelector(".tog").addEventListener("click", () => { if (enabled.has(a.id)) enabled.delete(a.id); else enabled.add(a.id); refresh(); });
    }
    row.querySelector(".sw-title").addEventListener("click", () => openDetail({type: "action", id: a.id}, true));
    box[gk].appendChild(row);
  }));
  renderBottomBar();
}
function renderBottomBar(){
  const open = D.actions.filter(switchable), on = open.filter(a => enabled.has(a.id)).length;
  $("#bbMain").textContent = `${on} of ${open.length} actions on`;
  $("#bbSub").textContent = `Best role expected ${Math.round(jp("best").exp.end)} by ${shortDate(D.meta.end)}`;
}
function renderMetrics(){
  $("#metrics").innerHTML = D.metrics.length ? D.metrics.map(m => { const d = r1(m.current - m.start);
    return `<div class="metric"><span>${esc(m.name)}${d ? `<div class="tiny" style="color:${d > 0 ? "var(--ok)" : "var(--sub)"};font-weight:650">${d > 0 ? "+" : ""}${d} since Day 1</div>` : ""}</span><span class="num"><b>${esc(m.current)}</b> <span class="sub">/ ${esc(m.target)}</span></span></div>`; }).join("")
    : '<div class="small sub">No north-star metrics in the plan yet.</div>';
}
"""

JS_VIEWS = r"""
// ---------- views ----------
const VIEWS = [["level","Level up"],["orgs","Organisations"],["top","Path to the top band"],["moves","What moves you"],["roles","Roles"],["swot","SWOT and TOWS"],["plan","Plan"],["evidence","Evidence"],["market","Market"]]
  .filter(v => (v[0] !== "top" || D.ceil) && (v[0] !== "swot" || D.swot));
// Tabs: aria-selected and aria-controls, arrow keys move between them, and on a phone the row
// scrolls sideways with a visible hint (a fade and a chevron) while there are more tabs to see.
function renderViewSeg(focus){
  $("#viewSeg").innerHTML = VIEWS.map(v => { const on = state.view === v[0];
    return `<button role="tab" id="tab-${v[0]}" aria-selected="${on}" aria-controls="v-${v[0]}" tabindex="${on ? 0 : -1}" data-v="${v[0]}">${v[1]}</button>`; }).join("");
  const tabs = [...$("#viewSeg").querySelectorAll("[role=tab]")];
  tabs.forEach((b, i) => { b.addEventListener("click", () => { state.view = b.dataset.v; renderViewSeg(); showView(); });
    b.addEventListener("keydown", e => { const k = {ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1}[e.key];
      if (k == null) return; e.preventDefault(); state.view = tabs[(k + tabs.length) % tabs.length].dataset.v; renderViewSeg(true); showView(); }); });
  VIEWS.forEach(v => $("#v-" + v[0]).setAttribute("aria-labelledby", "tab-" + v[0]));
  const sel = $("#viewSeg [aria-selected=true]"), seg = $("#viewSeg");
  if (sel && seg.scrollWidth > seg.clientWidth) seg.scrollLeft = Math.max(0, sel.offsetLeft - (seg.clientWidth - sel.offsetWidth) / 2);
  if (sel && focus) sel.focus();
  scrollHint(seg);
}
function scrollHint(row){
  const wrap = row.parentElement;
  if (!wrap || !wrap.classList.contains("hscroll")) return;
  const upd = () => { wrap.classList.toggle("more-right", row.scrollLeft + row.clientWidth < row.scrollWidth - 2); wrap.classList.toggle("more-left", row.scrollLeft > 2); };
  if (!row.dataset.hint){ row.dataset.hint = "1"; row.addEventListener("scroll", upd, {passive: true}); }
  upd();
}
function showView(animate){
  ["level","orgs","top","moves","roles","swot","plan","evidence","market"].forEach(v => $("#v-" + v).classList.toggle("on", v === state.view));
  ({level: renderLevel, orgs: renderOrgs, top: renderTop, moves: renderMoves, roles: renderRoles, swot: renderSwot, plan: renderPlan, evidence: renderEvidence, market: renderMarket})[state.view]();
  if (state.view !== "level") $("#v-" + state.view).insertAdjacentHTML("afterbegin", `<h2 class="sr-only">${esc(VIEWS.find(v => v[0] === state.view)[1])}</h2>`);
  if (animate !== false) enter($("#v-" + state.view));
}
function ring(g, today, exp){
  const R = 30, C = 2 * Math.PI * R, c = orgColour(g);
  return `<svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
    <circle cx="42" cy="42" r="${R}" fill="none" stroke="var(--rule)" stroke-width="8"/>
    <circle class="ring-arc" cx="42" cy="42" r="${R}" fill="none" stroke="${c}" stroke-opacity=".35" stroke-width="8" stroke-linecap="round" stroke-dasharray="${C * exp / 100} ${C}" transform="rotate(-90 42 42)"/>
    <circle class="ring-arc" cx="42" cy="42" r="${R}" fill="none" stroke="${c}" stroke-width="8" stroke-linecap="round" stroke-dasharray="${C * today / 100} ${C}" transform="rotate(-90 42 42)"/>
    <text class="ring-num" x="42" y="49" text-anchor="middle">${Math.round(today)}</text></svg>`;
}
function trail(g, r){
  const W2 = 260, H2 = 84, exp = jp(g).exp, best = jp(g).best, c = orgColour(g);
  const prev = D.runs.map(rn => rn.orgs[g]).filter(v => v != null);
  const lo = Math.max(0, Math.floor(Math.min(r.fit, ...prev) / 5) * 5 - 10), hi = 75;   // zoomed so the climb shows; the green line is the offer zone
  const xx = t => 6 + (t - T0) / (T1 - T0) * (W2 - 12), yy = v => H2 - 6 - (Math.max(lo, v) - lo) / (hi - lo) * (H2 - 12);
  const path = pts => SAMPLE_T.filter((_, i) => i % 4 === 0 || i === N - 1).map((t, i) => (i ? "L" : "M") + xx(t).toFixed(1) + "," + yy(valueAt(pts, t)).toFixed(1)).join(" ");
  const hist = D.runs.map(rn => ({t: tOf(rn.date), v: rn.date === TODAY ? r.fit : rn.orgs[g]})).filter(p => p.v != null);
  return `<svg viewBox="0 0 ${W2} ${H2}" style="width:100%;height:auto;margin-top:8px" role="img" aria-label="Trail for ${esc(D.orgs[g].name)}">
    <line x1="6" x2="${W2 - 6}" y1="${yy(70)}" y2="${yy(70)}" stroke="var(--ok)" stroke-dasharray="4 3"/>
    <path d="M${xx(TN)},${yy(r.fit)} L${W2 - 6},${yy(r.fit)}" fill="none" stroke="var(--stop)" stroke-width="2" stroke-dasharray="2 4"/>
    <path d="${path(best.pts)}" fill="none" stroke="${c}" stroke-width="2" stroke-dasharray="6 4"/>
    <path d="${path(exp.pts)}" fill="none" stroke="${c}" stroke-width="2"/>
    ${hist.length > 1 ? `<path d="${hist.map((p, i) => (i ? "L" : "M") + xx(p.t).toFixed(1) + "," + yy(p.v).toFixed(1)).join(" ")}" fill="none" stroke="var(--ink)" stroke-width="2"/>` : ""}
    <circle cx="${xx(TN)}" cy="${yy(r.fit)}" r="4" fill="var(--ink)"/></svg>`;
}
function renderOrgs(){
  $("#v-orgs").innerHTML = `<div class="grid2">${D.orgOrder.map(g => {
    const L = D.orgs[g], r = roleById[L.best]; if (!r) return "";
    if (!L.judged) return `<div class="card org-card" tabindex="0" data-org="${esc(g)}">
      <div class="org-name"><i class="org-key" style="background:${orgColour(g)}"></i>${esc(L.name)}</div>
      <h3 style="margin:10px 0 4px">No role judged yet at ${esc(L.name)}</h3>
      <div class="small sub">${esc(plural(L.count, "matching role"))} open, none judged, so there is no fit or interview chance to show yet. The next run can judge them.</div>
      <div class="kv" style="margin-top:8px"><span>Roles with an eligibility blocker</span><b class="num">${L.blocked} of ${L.count}</b></div>
    </div>`;
    const J = jp(g), exp = J.exp, m = J[state.mode], ib = m ? interviewBand(m.end, m.scores, m.r.hrl) : r.ib, sr = m ? m.r : r;   // the organisation's journey and the role holding its number
    return `<div class="card org-card" tabindex="0" data-org="${esc(g)}">
      <div class="org-head">${ring(g, m ? m.end : r.fit, exp.end)}<div style="min-width:0"><div class="org-name"><i class="org-key" style="background:${orgColour(g)}"></i>${esc(L.name)}</div>
      <div class="small sub">${esc(sr.title)}${L.members.length > 1 ? ", " + esc(sr.on) : ""}</div></div></div>
      <div class="kv" style="margin-top:8px"><span>Interview chance, ${esc(state.mode === "today" ? "now" : state.mode === "exp" ? "plan expected" : "plan best case")}</span>${pill(ib)}</div>
      <div class="kv"><span>Expected by ${esc(shortDate(D.meta.end))}</span><b class="num">${Math.round(exp.end)}</b></div>
      <div class="kv"><span>Roles with an eligibility blocker</span><b class="num">${L.blocked} of ${L.count}</b></div>
      ${trail(g, r)}
      <div class="tiny sub">Trail: black measured, solid expected, dashed best case, dotted do nothing</div>
    </div>`; }).join("")}</div>
    <div class="card" style="margin-top:16px"><div class="eyebrow">Outlook</div><h3>Chance of reaching your goal within ${esc(D.meta.horizon)} months: ${pill(D.meta.outlook.band)}</h3>
    <p class="small" style="margin:8px 0">${esc(D.meta.outlook.text)}</p><ul class="small sub">${D.meta.outlook.reasons.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>`;
  $("#v-orgs").querySelectorAll(".org-card").forEach(c => onEnter(c, () => openDetail({type: "org", id: c.dataset.org}, true)));
}
// ---------- Path to the top band (from eval/ceilings.json; today's numbers from the latest run) ----------
const an = n => /^(8|11|18)/.test(String(n)) ? "an" : "a";      // "an 85", "a 90"
const li = list => `<ul class="small">${list.map(x => `<li>${esc(x)}</li>`).join("")}</ul>`;
function renderTop(){
  const X = D.ceil, best = D.roles[0], T = X.target;
  const at = v => Math.max(0, Math.min(100, v));
  const rows = X.reach.map(p => {
    const c = orgColour(p.g), hist = p.ceilHist > p.ceil;
    const tipText = `${p.title}, ${p.on}. Today ${Math.round(p.now)}, likely in 12 months ${Math.round(p.likely)}, ceiling ${Math.round(p.ceil)}${hist ? `, or ${Math.round(p.ceilHist)} once your history is confirmed` : ""}.${p.binding ? " Holding it back most: " + p.binding + "." : ""}${p.open ? "" : " No longer open."}`;
    return `<div class="p90-row" tabindex="0" data-tip="${esc(tipText)}"${p.open ? ` data-role-open="${esc(p.id)}"` : ""}>
      <div><div class="p90-name"><i class="org-key" style="background:${c};margin-right:6px"></i>${esc(p.title)}</div><div class="tiny sub">${esc(p.on)}${p.loc ? " · " + esc(p.loc) : ""}${p.open ? "" : " · no longer open"}</div>
        <div class="tiny sub num p90-nums">Today <b>${Math.round(p.now)}</b> · likely <b>${Math.round(p.likely)}</b> · ceiling <b>${Math.round(p.ceil)}</b>${hist ? `, or <b>${Math.round(p.ceilHist)}</b> with history` : ""}</div></div>
      <div class="p90-track"><div class="base"></div><div class="p90-guide g70" style="left:70%"></div><div class="p90-guide gt" style="left:${at(T)}%"></div>
        <div class="span" style="left:${at(p.now)}%;width:${Math.max(0, at(p.ceil) - at(p.now))}%;background:${c}"></div>
        ${hist ? `<div class="ext" style="left:${at(p.ceil)}%;width:${at(p.ceilHist) - at(p.ceil)}%"></div><span class="mk hist" style="left:${at(p.ceilHist)}%"></span>` : ""}
        <span class="mk ceil" style="left:${at(p.ceil)}%"></span><span class="mk likely" style="left:${at(p.likely)}%;background:${c}"></span><span class="mk now" style="left:${at(p.now)}%"></span></div></div>`;
  }).join("");
  const ticks = [...new Set([0, 40, 55, 70, T, 100])].sort((a, b) => a - b);
  const axis = `<div class="p90-axis-row"><div></div><div class="p90-axis">${ticks.map(v => `<span style="left:${v}%;${v === 0 ? "transform:none" : v === 100 ? "transform:translateX(-100%)" : ""}">${v}</span>`).join("")}</div></div>`;
  const O = X.odds, w = X.watch, k0 = X.reach.length ? orgColour(X.reach[0].g) : "var(--accent)";
  const watchHTML = [["Role titles", w.titles], ["Places, in order", w.places], ["Good signs in a posting", w.good], ["Skipped", w.exclude]].filter(x => x[1].length).map(x => `<div class="f5-k">${x[0]}</div>${li(x[1])}`).join("");
  $("#v-top").innerHTML = `<div class="card"><div class="eyebrow">Path to the top band</div><h3>What ${an(T)} ${T} takes</h3><p class="small" style="margin:6px 0 0">${esc(X.how)}</p>
      ${X.counts.length ? `<div class="p90-tiles">${X.counts.map(t => `<div class="tile3"><div class="v num">${esc(t[0])}</div><div class="l">${esc(t[1])}</div></div>`).join("")}</div>` : ""}</div>
    ${X.reach.length ? `<div class="card"><div class="eyebrow">Roles that can reach ${T}</div><h3>Today, likely in 12 months, and the ceiling</h3>
      <p class="small sub" style="margin:0 0 8px">Ceiling means every factor at the most your evidence could support. Today's number comes from the latest scored day; the rest from the analysis of ${esc(fmtDate(X.generated))}. Tap a role to drill in.</p>
      <div>${rows}</div>${axis}
      <div class="legend"><span><i class="p90-key" style="background:var(--ink)"></i>Today</span><span><i class="p90-key" style="background:${k0}"></i>Likely in 12 months, in the organisation's colour</span>
        <span><i class="p90-key" style="background:var(--card);border:2.5px solid var(--ink)"></i>Ceiling on evidence you can show</span><span><i class="p90-key" style="background:var(--card);border:2px dashed var(--line)"></i>Ceiling once your history is confirmed</span>
        <span style="color:var(--ok)"><i class="lk" style="border-top-style:dashed"></i><span class="sub">Offer zone starts at 70</span></span><span style="color:var(--accent)"><i class="lk"></i><span class="sub">${T}</span></span></div>
      <details class="tableview"><summary>Show as a table</summary><div class="tscroll"><table><tr><th>Role</th><th>Today</th><th>Likely in 12 months</th><th>Ceiling</th><th>If history confirmed</th></tr>${X.reach.map(p => `<tr><td>${esc(p.title)}<div class="tiny sub">${esc(p.on)}${p.loc ? " · " + esc(p.loc) : ""}</div></td><td class="num">${Math.round(p.now)}</td><td class="num">${Math.round(p.likely)}</td><td class="num">${Math.round(p.ceil)}</td><td class="num">${Math.round(p.ceilHist)}</td></tr>`).join("")}</table></div></details></div>` : ""}
    ${O.statement || O.top || O.good ? `<div class="card"><div class="eyebrow">Honest odds</div>
      <div class="odds"><div><div class="tiny sub">Reach ${T} or more on one open role within 12 months</div><b>${esc(cap1(O.top) || "Not judged yet")}</b></div><div><div class="tiny sub">Reach 70 or more, a good interview chance${O.goodBy ? ", by " + esc(fmtDate(O.goodBy)) : ""}</div><b>${esc(cap1(O.good) || "Not judged yet")}</b></div></div>
      <p class="small">${esc(O.statement)}</p>${O.why.length ? `<div class="f5-k">Why not higher</div>${li(O.why)}` : ""}</div>` : ""}
    ${X.factors.length ? `<div class="eyebrow" style="margin:22px 4px 10px">What 5 out of 5 looks like, factor by factor</div>
    <div class="grid2">${X.factors.map(f => { const k = DIMS.indexOf(f.dim);
      return `<div class="card f5"><div class="d-head"><h3 style="margin:0">${esc(D.dimNames[f.dim])}</h3><span class="tiny sub" style="white-space:nowrap">weight ${W[k]}</span></div>
        <div class="kv" style="padding:6px 0 0"><span>Your best role today</span><span>${dotRow(best.s[k], best.s[k])} <b class="num">${best.s[k]}</b>/5</span></div>
        ${f.now ? `<div class="f5-k">Now</div><div class="small">${esc(f.now)}</div>` : ""}
        ${f.five ? `<div class="f5-k">What 5 out of 5 looks like</div><div class="small">${esc(f.five)}</div>` : ""}
        ${f.gap ? `<div class="f5-k">The gap</div><div class="small">${esc(f.gap)}</div>` : ""}
        ${f.moves.length ? `<div class="f5-k">Moves</div>${li(f.moves)}` : ""}
        ${f.effort ? `<div class="f5-k">Effort</div><div class="small">${esc(f.effort)}</div>` : ""}
        ${f.chance ? `<div class="f5-k">Chance it works</div><div class="small">${esc(f.chance)}</div>` : ""}</div>`; }).join("")}</div>` : ""}
    ${X.phases.length ? `<div class="card" style="margin-top:16px"><div class="eyebrow">Roadmap</div><h3>${plural(X.phases.length, "phase")} to ${an(T)} ${T}</h3>
      <div class="phases" style="margin-top:10px">${X.phases.map(p => `<div class="phase"><div class="ph-n">${esc(p.phase)}</div><div class="tiny sub">${esc(p.window)}</div>${p.steps.length ? li(p.steps) : `<div class="small sub" style="margin-top:6px">Where you start, measured.</div>`}</div>`).join("")}</div>
      ${X.roadmap.length ? `<div class="f5-k" style="margin-top:18px">Where ${X.roadmap.length === 1 ? "one anchor role lands" : X.roadmap.length + " anchor roles land"} at each phase</div>
      <div class="tiny sub">Big number: the likely fit. Below it: the fit if every step lands, and the interview chance that would give.</div>
      ${X.roadmap.map(r => `<div style="font-weight:650;margin-top:14px">${esc(r.label)}</div><div class="rm">${r.phases.map(ph => `<div><div class="tiny sub">${esc(ph.phase)}</div><b class="num">${Math.round(ph.likely)}</b><div class="tiny sub">${Math.round(ph.full)} if every step lands</div>${BANDS.indexOf(ph.band) >= 0 ? pill(ph.band) : ""}</div>`).join("")}</div>`).join("")}` : ""}</div>` : ""}
    ${X.create.length || watchHTML ? `<div class="grid2" style="margin-top:16px">
      ${X.create.length ? `<div class="card"><div class="eyebrow">Create the role</div>${X.create.map((c, i) => `<div style="padding:10px 0;${i ? "border-top:1px solid var(--rule)" : ""}"><div style="font-weight:650">${esc(c.t)}</div><div class="small">${esc(c.how)}</div>${c.lifts ? `<div class="tiny sub" style="margin-top:4px">Lifts: ${esc(c.lifts)}</div>` : ""}</div>`).join("")}</div>` : ""}
      ${watchHTML ? `<div class="card watch"><div class="eyebrow">What each run watches for</div><div class="small">${esc(w.rule)}</div>${watchHTML}</div>` : ""}</div>` : ""}`;
  bindTips($("#v-top"));
  $("#v-top").querySelectorAll("[data-role-open]").forEach(n => onEnter(n, () => openDetail({type: "role", id: n.dataset.roleOpen}, true)));
}
function renderMoves(){
  const max = Math.max(1, ...D.gaps.map(g => g.points));
  $("#v-moves").innerHTML = `<div class="card"><div class="eyebrow">What would lift your odds most</div>
    <p class="small sub" style="margin:0 0 8px">Fit points gained, added up across your top roles. Hover a bar for the detail.</p>
    <div>${D.gaps.map(g => `<div class="gbar" tabindex="0" data-tip="${esc(g.title)}: +${g.points} points across ${plural(g.roles, "role")}. ${esc(g.why)}"><div class="small">${esc(g.title)}</div><div class="gtrack"><div class="gfill" style="width:${Math.max(3, g.points / max * 100)}%"></div><span class="small num" style="font-weight:650">+${g.points}</span></div></div>`).join("") || '<div class="small sub">No gaps listed yet.</div>'}</div>
    <details class="tableview"><summary>Show as a table</summary><div class="tscroll"><table><tr><th>Gap</th><th>Points</th><th>Roles</th></tr>${D.gaps.map(g => `<tr><td>${esc(g.title)}</td><td class="num">${g.points}</td><td class="num">${g.roles}</td></tr>`).join("")}</table></div></details></div>
    <div class="card"><div class="eyebrow">Questions only you can answer</div><p class="small sub" style="margin:0 0 6px">Each answer unlocks points the eval can't count yet.</p>
    ${D.vtu.map(v => `<div style="padding:10px 0;border-top:1px solid var(--rule)"><div style="font-weight:600;font-size:15px">${esc(v.q)}</div><div class="small sub">What it unlocks: ${esc(v.why)}</div></div>`).join("") || '<div class="small sub">None right now.</div>'}</div>`;
  bindTips($("#v-moves"));
}
const roleFilter = {org: "", fam: "", loc: "", elig: ""};
function renderRoles(){
  const opt = (o, v) => Object.keys(o).map(k => `<option value="${esc(k)}" ${v === k ? "selected" : ""}>${esc(o[k])}</option>`).join("");
  const orgsO = {}; [...new Set(D.roles.map(r => r.org))].forEach(o => orgsO[o] = D.orgNames[o] || o);
  $("#v-roles").innerHTML = `<div class="filters">
    <select id="fOrg" aria-label="Organisation"><option value="">All organisations</option>${opt(orgsO, roleFilter.org)}</select>
    <select id="fFam" aria-label="Role type"><option value="">All role types</option>${opt(D.families, roleFilter.fam)}</select>
    <select id="fLoc" aria-label="Location"><option value="">All locations</option>${opt(D.locations, roleFilter.loc)}</select>
    <select id="fElig" aria-label="Eligibility"><option value="">Open and blocked</option><option value="open" ${roleFilter.elig === "open" ? "selected" : ""}>Open to you</option><option value="blocked" ${roleFilter.elig === "blocked" ? "selected" : ""}>Has an eligibility blocker</option></select>
    <span class="small sub" id="fCount"></span></div>
    <div class="card"><div class="eyebrow">Roles by factor, ${esc(modeName())}</div><div class="tiny sub" style="margin-bottom:8px">Each cell is a factor score out of 5. The stronger the score, the more the cell stands out from the page. Tap a role to drill in.</div><div class="heat-wrap" id="heatWrap"></div></div>`;
  ["fOrg","fFam","fLoc","fElig"].forEach((id, i) => $("#" + id).addEventListener("change", e => { roleFilter[["org","fam","loc","elig"][i]] = e.target.value; fillHeat(); }));
  fillHeat();
}
const JUDGED_DIMS = ["D1", "D2", "D4"];   // judged per role; until then they are "not judged", not 0
function cellStyle(v){ const k = Math.max(0, Math.min(5, Math.round(v))); return `background:var(--h${k});color:${k >= 3 ? "var(--hdt)" : "var(--hlt)"}`; }
function fillHeat(){
  const list = D.roles.filter(r => (!roleFilter.org || r.org === roleFilter.org) && (!roleFilter.fam || r.family === roleFilter.fam) && (!roleFilter.loc || r.lc === roleFilter.loc) && (!roleFilter.elig || (roleFilter.elig === "blocked") === r.blocked))
    .sort((a, b) => (b.judged - a.judged) || (fitM(b) - fitM(a)));   // judged first: an unjudged role has no real fit
  const nj = list.filter(r => !r.judged).length;
  $("#fCount").textContent = plural(list.length, "role") + (nj ? `, ${nj} not judged yet` : "");
  const shown = list.slice(0, 80);
  const short = ["Match","Proof","Warm path","Edge","Signal","Eligible","Ready"];
  $("#heatWrap").innerHTML = list.length ? `<table class="heat"><thead><tr><th>Role</th>${DIMS.map((d, k) => `<th title="${esc(D.dimNames[d])}">${short[k]}<div class="tiny sub">${W[k]}</div></th>`).join("")}<th>Fit</th></tr></thead><tbody>${shown.map(r => { const s = scoresM(r);
    return `<tr${r.judged ? "" : ' class="nj"'}><td class="name" data-role-open="${esc(r.id)}"><div class="row-title small"><i class="org-key" style="background:${orgColour(r.g)};margin-right:6px"></i>${esc(r.title)}</div><div class="tiny sub">${esc(r.on)} · ${esc(r.loc.slice(0, 1).join(""))}${r.blocked ? " · eligibility blocker" : ""}${r.judged ? "" : " · not judged yet"}</div></td>
    ${s.map((v, k) => !r.judged && JUDGED_DIMS.includes(DIMS[k]) ? `<td><div class="cell nj" data-tip="${esc(D.dimNames[DIMS[k]])}: not judged yet.">?</div></td>` : `<td><div class="cell" style="${cellStyle(v)}" data-tip="${esc(D.dimNames[DIMS[k]])}: ${r1(v)} of 5. ${esc(r.n[k])}">${Number.isInteger(v) ? v : v.toFixed(1)}</div></td>`).join("")}
    <td>${r.judged ? `<div class="cell" style="background:var(--card2);color:var(--ink)">${Math.round(fitM(r))}</div>` : '<div class="cell nj tiny" data-tip="Not judged yet, so no fit score.">Not judged</div>'}</td></tr>`; }).join("")}</tbody></table>
    ${list.length > shown.length ? `<div class="small sub" style="margin-top:8px">Showing the top ${shown.length} of ${list.length}. Narrow the filters to see more.</div>` : ""}` : '<div class="small sub">No roles match these filters.</div>';
  bindTips($("#heatWrap"));
  $("#heatWrap").querySelectorAll("[data-role-open]").forEach(n => n.addEventListener("click", () => openDetail({type: "role", id: n.dataset.roleOpen}, true)));
}
const evChip = id => `<span class="chip" data-ev="${esc(id)}">${esc(id)}</span>`;
function actChip(id){ const a = D.actions.find(x => x.id === id); return a ? `<span class="chip" data-act="${esc(id)}">${esc(a.title)}</span>` : ""; }
function bindChips(root){
  root.querySelectorAll(".chip[data-ev]").forEach(c => c.addEventListener("click", e => { e.stopPropagation(); openDetail({type: "evidence", id: c.dataset.ev}, false); }));
  root.querySelectorAll(".chip[data-act]").forEach(c => c.addEventListener("click", e => { e.stopPropagation(); openDetail({type: "action", id: c.dataset.act}, false); }));
}
function swotGrid(G){
  const q = (k, name) => `<div class="card swot-q"><h3>${name}</h3>${G[k].length ? `<ul>${G[k].map(i => `<li class="small">${esc(i.t)}<div>${i.ev.map(evChip).join("")}${i.src ? `<div class="tiny sub">Source: ${esc(i.src)}</div>` : ""}</div></li>`).join("")}</ul>` : '<div class="small sub">None recorded.</div>'}</div>`;
  return `<div class="grid2">${q("S","Strengths")}${q("W","Weaknesses")}${q("O","Opportunities")}${q("T","Threats")}</div>`;
}
function renderSwot(){
  const S = D.swot, [overall, ...rest] = S.grids;
  $("#v-swot").innerHTML = `<div class="small sub" style="margin:0 0 10px">Strengths and weaknesses are about you, each backed by evidence; opportunities and threats are about the market.</div>
    ${swotGrid(overall)}
    ${S.tows.length ? `<div class="card" style="margin-top:16px"><div class="eyebrow">TOWS: turning the grid into moves</div><div class="tows">${S.tows.map(t => `<div class="k">${esc(t.k)}</div><div><div style="font-weight:600">${esc(t.t)}</div><div class="tiny sub">${esc(t.name)} · ${esc(t.scope)} · uses ${esc(t.uses.join(", "))}</div><div>${t.a.map(actChip).join("")}</div></div>`).join("")}</div></div>` : ""}
    ${rest.length ? `<div class="grids">${rest.map(G => `<details><summary>${esc(G.name)}: its own grid</summary>${swotGrid(G)}</details>`).join("")}</div>` : ""}`;
  bindChips($("#v-swot"));
}
// Badges and the action list follow the one ranked list too: done first for the badges, then Do next order.
const STATUS_RANK = {doing: 0, todo: 1, later: 2, done: 3, dropped: 4};
function renderPlan(){
  const L = lv(), Q = {}, acts = D.actions.filter(a => a.status !== "dropped");
  L.qs.forEach(q => Q[q.a.id] = q);
  const rest = D.actions.filter(a => !Q[a.id]).sort((x, y) => (STATUS_RANK[x.status] - STATUS_RANK[y.status]) || (x.status === "done" ? tOf(y.date) - tOf(x.date) : tOf(x.date) - tOf(y.date)));
  const order = L.up.map(q => q.a).concat(rest), badges = rest.filter(a => a.status === "done").concat(order.filter(a => a.status !== "done" && a.status !== "dropped"));
  let step = 0;
  const PW = Math.max(300, ($("#hero").clientWidth || 760) - 40), PH = 40 + acts.length * 34;
  const col = Math.min(170, Math.round(PW * 0.42)), maxCh = Math.floor(col / 6.6);
  const xa = iso => col + (Math.max(T0, Math.min(T1, tOf(iso))) - T0) / (T1 - T0) * (PW - col - 46), todayX = xa(TODAY);
  let svg = `<svg viewBox="0 0 ${PW} ${PH}" style="width:100%;height:auto" role="img" aria-label="Plan timeline"><line x1="${todayX}" x2="${todayX}" y1="10" y2="${PH - 6}" stroke="var(--accent)" stroke-dasharray="3 3"/><text x="${todayX + 4}" y="18" font-size="11" font-weight="650" fill="var(--accent)">Today</text>`;
  acts.forEach((a, i) => {
    const y = 36 + i * 34, x = xa(a.date), on = enabled.has(a.id) || a.status === "done", c = a.status === "done" ? "var(--ok)" : a.status === "doing" ? "var(--accent)" : "var(--line)";
    svg += `<text x="0" y="${y + 4}" font-size="12" font-weight="${on ? 600 : 400}" fill="${on ? "var(--ink)" : "var(--sub)"}">${esc(a.title.length > maxCh ? a.title.slice(0, maxCh - 1) + "…" : a.title)}</text>`;
    svg += `<line x1="${Math.min(todayX, x)}" x2="${Math.max(todayX, x)}" y1="${y}" y2="${y}" stroke="${c}" stroke-width="4" stroke-linecap="round" stroke-opacity="${on ? .45 : .2}"/>`;
    svg += `<circle cx="${x}" cy="${y}" r="7" fill="${on ? c : "var(--card)"}" stroke="${c}" stroke-width="2" data-act="${esc(a.id)}" style="cursor:pointer"/><text x="${x + 11}" y="${y + 4}" font-size="11" fill="var(--sub)">${a.dated || a.status === "done" ? shortDate(a.date) : "no date"}</text>`;
  });
  svg += "</svg>";
  $("#v-plan").innerHTML = `${D.meta.principle ? `<div class="card"><div class="eyebrow">The principle</div><div class="small">${esc(D.meta.principle)}</div></div>` : ""}
    <div class="card"><div class="eyebrow">Badges</div><div class="small sub" style="margin:-2px 0 12px">A badge unlocks when an action is done, with evidence.</div>
    <div class="badges">${badges.map(a => `<div class="badge ${esc(a.status)}" data-act="${esc(a.id)}"><div class="bi">${a.status === "done" ? "✓" : ++step}</div><div class="bt">${esc(a.title)}</div><div class="bs">${stName(a.status)}</div></div>`).join("") || '<div class="small sub">No actions yet.</div>'}</div></div>
    ${acts.length ? `<div class="card"><div class="eyebrow">Plan timeline</div>${svg}</div>` : ""}
    <div class="list" style="margin-top:16px">${order.map(a => { const q = Q[a.id];
      return `<div class="row" tabindex="0" data-act="${esc(a.id)}"><span class="status-dot ${esc(a.status)}"></span><div class="row-main"><div class="row-title">${esc(a.title)}</div>
      <div class="row-sub">${a.group === "now" ? "Now · " : a.group === "later" && a.status !== "later" ? "Later · " : ""}${stName(a.status)} · ${esc(a.owner)}${a.effort ? " · " + esc(a.effort) : ""} · ${a.status === "done" ? "done " + esc(fmtDate(a.date)) : a.dated ? "target " + esc(fmtDate(a.date)) : "no target date"} · ${Math.round(a.p * 100)}% chance</div>
      ${a.stale ? `<div class="tiny stale">No score or metric movement in ${a.stale} runs: rework it or drop it.</div>` : ""}</div>
      <div class="row-side"><span class="dn-p">${q ? points(q) || "credibility" : a.status === "done" ? "done" : ""}</span></div><span class="chev">›</span></div>`; }).join("")}</div>
    <div class="grid2" style="margin-top:16px">
      <div class="card"><div class="eyebrow">What was tried</div>${D.experiments.length ? D.experiments.map((x, i) => `<div style="padding:9px 0;${i ? "border-top:1px solid var(--rule)" : ""}"><div class="small" style="font-weight:600">${esc(x.action)} <span class="tag">${esc(cap1(x.decision))}</span></div><div class="small">${esc(x.result)}</div><div class="tiny sub">${esc(fmtDate(x.date))}${x.why ? ". " + esc(x.why) : ""}</div></div>`).join("") : '<div class="small sub">Nothing logged yet.</div>'}</div>
      <div class="card"><div class="eyebrow">Backlog</div>${D.backlog.length ? li(D.backlog) : '<div class="small sub">Empty.</div>'}</div></div>`;
  $("#v-plan").querySelectorAll("[data-act]").forEach(c => c.addEventListener("click", () => openDetail({type: "action", id: c.dataset.act}, true)));
}
const LEVELS = [["verified","Verified"],["corroborated","Corroborated"],["partially_verified","Partly verified"],["self_reported","Self-reported"],["unverified","Not verified yet"],["contradicted","Contradicted"]];
const levelName = s => (LEVELS.find(l => l[0] === s) || [s, s.replace(/_/g, " ")])[1];
const CLAIMS = {supported: "Supported", overstated: "Overstated", unsupported: "Unsupported", contradicted: "Contradicted", pending: "Waiting to be checked"};
const evFilter = {cat: ""};
function renderEvidence(){
  const counts = {}; D.evidence.forEach(e => counts[e.status] = (counts[e.status] || 0) + 1);
  const cats = [...new Set(D.evidence.map(e => e.cat))], lbl = s => cap1(s.replace(/_/g, " "));
  $("#v-evidence").innerHTML = `<div class="tiles5">${LEVELS.filter(([k]) => k !== "partially_verified" || counts[k]).map(([k, l]) => `<div class="tile"><div class="v num">${counts[k] || 0}</div><div class="l">${l}</div></div>`).join("")}</div>
    <div class="filters" style="margin-top:16px"><select id="evCat" aria-label="Kind of evidence"><option value="">All kinds</option>${cats.map(c => `<option value="${esc(c)}" ${evFilter.cat === c ? "selected" : ""}>${esc(lbl(c))}</option>`).join("")}</select></div><div class="list" id="evList"></div>
    ${D.claims.length ? `<div class="card" style="margin-top:16px"><div class="eyebrow">Your public claims, checked</div><div class="small sub" style="margin-bottom:6px">What you say about yourself in public, checked against the evidence. Fix overstated claims before you apply.</div>
      ${D.claims.map(c => `<div style="padding:10px 0;border-top:1px solid var(--rule)"><div class="small" style="font-weight:550">${esc(c.text)} <span class="tag t-${esc(c.status)}">${esc(CLAIMS[c.status] || c.status)}</span></div>${c.better ? `<div class="small sub">Better: ${esc(c.better)}</div>` : ""}<div>${c.ev.map(evChip).join("")}${c.url ? ` <a class="tiny" href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">Where it appears</a>` : ""}</div></div>`).join("")}</div>` : ""}`;
  const fill = () => { $("#evList").innerHTML = D.evidence.filter(e => !evFilter.cat || e.cat === evFilter.cat).map(e => `<div class="row" tabindex="0" data-ev-row="${esc(e.id)}"><span class="tiny sub num" style="width:34px;flex-shrink:0">${esc(e.id)}</span><div class="row-main"><div class="small" style="font-weight:550">${esc(e.claim)}</div><div class="row-sub tiny">${esc(lbl(e.cat))}</div></div><span class="tag t-${esc(e.status)}">${esc(levelName(e.status))}</span><span class="chev">›</span></div>`).join("") || '<div class="row"><span class="small sub">No evidence yet.</span></div>';
    $("#evList").querySelectorAll("[data-ev-row]").forEach(n => onEnter(n, () => openDetail({type: "evidence", id: n.dataset.evRow}, true))); };
  $("#evCat").addEventListener("change", e => { evFilter.cat = e.target.value; fill(); });
  bindChips($("#v-evidence"));
  fill();
}
function renderMarket(){
  const m = D.market, maxL = Math.max(1, ...D.orgOrder.map(g => D.orgs[g].count)), maxLoc = Math.max(1, ...Object.values(m.byLocation));
  const home = D.locations[m.home] || "your home region";
  $("#v-market").innerHTML = `<div class="tiles4" style="margin-top:0">
    <div class="tile"><div class="v num">${m.total}</div><div class="l">open roles match your role types${m.fetched ? `, out of ${m.fetched.toLocaleString("en-AU")} postings` : ""}</div></div>
    <div class="tile"><div class="v num">${m.homeCount}</div><div class="l">in ${esc(home)}</div></div>
    <div class="tile"><div class="v num">${m.new}</div><div class="l">new since the last fetch${m.closed ? `, ${m.closed} closed` : ""}</div></div>
    <div class="tile"><div class="v num">${m.blocked}</div><div class="l">have an eligibility blocker</div></div></div>
    <div class="grid2" style="margin-top:16px">
     <div class="card"><div class="eyebrow">Matching roles by organisation</div>${D.orgOrder.map(g => { const L = D.orgs[g]; return `<div class="gbar" tabindex="0" data-tip="${esc(L.name)}: ${plural(L.count, "role")}, ${L.blocked} with an eligibility blocker"><div class="small"><i class="org-key" style="background:${orgColour(g)};margin-right:6px"></i>${esc(L.name)}</div><div class="gtrack"><div class="gfill" style="width:${Math.max(3, L.count / maxL * 100)}%;background:${orgColour(g)}"></div><span class="small num">${L.count}</span></div></div>`; }).join("")}</div>
     <div class="card"><div class="eyebrow">Where the roles are</div>${Object.keys(D.locations).filter(k => m.byLocation[k]).map(k => `<div class="gbar" tabindex="0" data-tip="${esc(D.locations[k])}: ${plural(m.byLocation[k] || 0, "role")}"><div class="small">${esc(D.locations[k])}</div><div class="gtrack"><div class="gfill" style="width:${Math.max(3, (m.byLocation[k] || 0) / maxLoc * 100)}%"></div><span class="small num">${m.byLocation[k] || 0}</span></div></div>`).join("")}</div></div>
    <div class="card" style="margin-top:16px"><div class="eyebrow">Role types by organisation</div><div class="tscroll"><table><tr><th>Organisation</th>${Object.values(D.families).map(f => `<th>${esc(f)}</th>`).join("")}</tr>${Object.keys(m.byOrgFamily).map(o => `<tr><td>${esc(D.orgNames[o] || o)}</td>${Object.keys(D.families).map(f => `<td class="num">${m.byOrgFamily[o][f] || 0}</td>`).join("")}</tr>`).join("")}</table></div>${m.fetchedOn ? `<div class="tiny sub" style="margin-top:6px">Postings fetched ${esc(fmtDate(m.fetchedOn))}.</div>` : ""}</div>
    <div class="eyebrow" style="margin-top:20px">Roles in ${esc(home)}</div>
    <div class="list">${D.roles.filter(r => r.lc === m.home && r.judged).slice(0, 40).map(r => `<div class="row" data-role-row="${esc(r.id)}"><i class="org-key" style="background:${orgColour(r.g)}"></i><div class="row-main"><div class="row-title">${esc(r.title)}</div><div class="row-sub">${esc(r.on)} · ${esc(r.loc.join(", "))}</div></div><div class="row-side"><b>${Math.round(fitM(r))}</b></div><span class="chev">›</span></div>`).join("") || `<div class="row"><span class="small sub">${m.homeCount ? "None judged yet." : "None open right now."}</span></div>`}</div>
    ${D.roles.some(r => r.lc === m.home && !r.judged) ? `<div class="tiny sub" style="margin-top:6px">${esc(plural(D.roles.filter(r => r.lc === m.home && !r.judged).length, "more role"))} here not judged yet, so not scored.</div>` : ""}`;
  bindTips($("#v-market"));
  $("#v-market").querySelectorAll("[data-role-row]").forEach(n => n.addEventListener("click", () => openDetail({type: "role", id: n.dataset.roleRow}, true)));
}
"""

JS_LEVELS = r"""
// ---------- level up: the next level, quests, level history and streak ----------
// Mirrors scripts/_levels.py (same order of operations, same tie-breaks). Every number is
// derived from the scored runs and the plan's effects: no experience points, nothing invented.
const MAX_EXACT = 14;
const fmtP = v => String(r1(v));
const pctOf = p => Math.floor(p * 100 + 0.5);
const hoursOf = list => list.reduce((t, a) => t + (a.hours || 0), 0);
const raisesL = (r, a) => walkL(r, [a], "best").scores.some((v, k) => v > r.s[k] + 1e-9);
function keyLess(a, b){ for (let i = 0; i < a.length; i++){ if (a[i] < b[i]) return true; if (a[i] > b[i]) return false; } return false; }
function combos(list, k, f){ const idx = []; (function rec(start){ if (idx.length === k){ f(idx.map(i => list[i])); return; }
  for (let i = start; i < list.length; i++){ idx.push(i); rec(i + 1); idx.pop(); } })(0); }
// The fewest actions that take the best fit across rs to T. Ties: earliest date, least effort, higher fit, ids.
function smallestSet(rs, acts, T, mode){
  if (!rs.length || bestOf(rs, acts, mode).end < T) return null;
  if (acts.length > MAX_EXACT) return greedySet(rs, acts, T, mode);
  for (let k = 1; k <= acts.length; k++){
    let best = null;
    combos(acts, k, c => { const w = bestOf(rs, c, mode); if (w.end < T) return;
      const key = [crossDate(w.pts, T), hoursOf(c), -w.end, c.map(a => a.id).join(",")];
      if (!best || keyLess(key, best.key)) best = {key, c, w}; });
    if (best) return {ids: best.c.map(a => a.id), acts: best.c, date: crossDate(best.w.pts, T), fit: best.w.end, exact: true, role: best.w.r};
  }
  return null;
}
function greedySet(rs, acts, T, mode){
  const fit = list => bestOf(rs, list, mode).end, inOrder = list => acts.filter(a => list.indexOf(a) >= 0);
  let chosen = [];
  while (fit(chosen) < T){
    const cur = fit(chosen); let pick = null, rate = -1;
    acts.forEach(a => { if (chosen.indexOf(a) >= 0) return; const g = fit(inOrder(chosen.concat([a]))) - cur, q = g / (a.hours || 1); if (g > 0 && q > rate){ pick = a; rate = q; } });
    if (!pick) return null;
    chosen = inOrder(chosen.concat([pick]));
  }
  for (let i = chosen.length - 1; i >= 0; i--){ const rest = chosen.filter((_, j) => j !== i); if (fit(rest) >= T) chosen = rest; }
  const w = bestOf(rs, chosen, mode);
  return {ids: chosen.map(a => a.id), acts: chosen, date: crossDate(w.pts, T), fit: w.end, exact: false, role: w.r};
}
// The chance these actions really get any of rs there, treating each action's chance as independent.
function chanceOf(rs, acts, T){
  const n = acts.length; if (n > MAX_EXACT) return null;
  let total = 0;
  for (let m = 0; m < (1 << n); m++){
    let pr = 1; const works = [];
    acts.forEach((a, i) => { if ((m >> i) & 1){ pr *= a.p; works.push(a); } else pr *= 1 - a.p; });
    if (pr > 0 && rs.some(r => walkL(r, works, "best").end >= T)) total += pr;
  }
  return total;
}
// The next level on the best fit across rs (today's best first): any of them can carry it.
function nextLevel(rs){
  const r = rs[0], acts = D.actions.filter(a => switchable(a) && enabled.has(a.id));
  const idx = bandIdx(r.fit), o = {r, fit: r.fit, level: idx + 1, band: BANDS[idx], top: idx >= 4};
  if (o.top) return o;
  const T = THRESH[idx + 1], rel = acts.filter(a => rs.some(x => raisesL(x, a))), every = bestOf(rs, acts, "exp");
  Object.assign(o, {target: T, nextLevel: idx + 2, nextBand: BANDS[idx + 1], toNext: r1(T - r.fit),
    plan: {exp: every.end, best: bestOf(rs, acts, "best").end, date: crossDate(every.pts, T)}});
  // Only roles that could reach the line if every helpful action worked can carry the level there.
  const cands = rs.filter(x => walkL(x, rel, "best").end >= T), use = rel.filter(a => cands.some(x => raisesL(x, a)));
  const set = smallestSet(cands, use, T, "exp");
  o.reachable = !!set;
  if (set){ set.chance = chanceOf(cands, set.acts, T); o.set = set; return o; }
  const bc = smallestSet(cands, use, T, "best");
  if (bc) bc.chance = chanceOf(cands, bc.acts, T);
  o.bestCase = bc;
  // What is missing: room under the caps on the role the whole plan takes closest.
  const m = every.r, ceil = m.s.map((v, k) => hardBlock(m, k) ? v : Math.min(5, v + CAPS[k]));
  const covered = DIMS.map((_, k) => rel.some(a => walkL(m, [a], "best").scores[k] > m.s[k] + 1e-9));
  o.missing = {points: r1(T - every.end), ceiling: fitOf(ceil), r: m,
    room: DIMS.map((d, k) => ({dim: d, k, points: r1((ceil[k] - every.scores[k]) * W[k] / 5 * 100 / TW), covered: covered[k]}))
      .filter(x => x.points > 0).sort((a, b) => (b.points - a.points) || (a.k - b.k))};
  return o;
}
// Each action on its own, as points toward the next level: the best fit across rs after it alone, minus the
// best fit today, on the role that then holds the best fit (q.r), with today's best role second (leadExp).
function questsFor(rs, nl){
  const lead = rs[0], crit = new Set(nl.set ? nl.set.ids : []), bc = new Set(nl.bestCase ? nl.bestCase.ids : []);
  const acts = D.actions.filter(a => live(a) || (a.status === "later" && enabled.has(a.id)));   // parked: only while switched on
  return acts.map(a => {
    const w = bestOf(rs, [a], "exp"), ok = bestOf(rs, [a], "exp", a.id);
    const exp = r1(w.end - lead.fit), works = r1(ok.end - lead.fit);
    return {a, exp, works, rate: a.hours ? exp / a.hours : 0, crit: crit.has(a.id), bc: bc.has(a.id), on: enabled.has(a.id),
      r: w.r, fitAfter: w.end, leadExp: r1(walkL(lead, [a], "exp").end - lead.fit), leadWorks: r1(walkL(lead, [a], "best").end - lead.fit)};
  }).sort((x, y) => (y.rate - x.rate) || (y.exp - x.exp) || (y.a.priority - x.a.priority) || (x.a.date < y.a.date ? -1 : x.a.date > y.a.date ? 1 : 0) || (x.a.id < y.a.id ? -1 : 1));
}
// ---------- one yardstick: the ranked list every action list follows ----------
// The actions on the path to the next level: the smallest set, or, when none gets there, the best-case set.
// Mirrors path_ids() in scripts/_levels.py.
function pathIds(nl){ if (nl.top) return []; const f = nl.reachable ? nl.set : nl.bestCase; return f ? f.ids.slice() : []; }
// The path first, in target-date order, then the rest as questsFor() sorts them. Mirrors up_next() in scripts/_levels.py.
function upNext(qs, nl){
  const path = new Set(pathIds(nl));
  const first = qs.filter(q => path.has(q.a.id)).sort((x, y) => (x.a.date < y.a.date ? -1 : x.a.date > y.a.date ? 1 : 0) || (x.a.id < y.a.id ? -1 : 1));
  return first.concat(qs.filter(q => !path.has(q.a.id)));
}
// The journey's next level, quests and Do next order, worked out once per refresh (recompute() and the organisation selector clear it).
function lv(){ if (!LV){ const rs = journeyRoles(), nl = nextLevel(rs), qs = questsFor(rs, nl); LV = {rs, nl, qs, up: upNext(qs, nl)}; } return LV; }
// The tag an action on the path carries in Do next and on its quest card. Mirrors path_tag() in _levels_html.py.
const pathTag = (q, nl) => q.crit ? `On the path to Level ${nl.nextLevel}` : q.bc && !nl.reachable ? "Needed for the best case" : null;
// The one points number an action shows everywhere outside the What if rail: expected points toward the next level, on its own.
const points = q => q.a.effects.length ? "+" + fmtP(Math.max(0, q.exp)) : null;
// Mirrors do_next_rows() in _levels_html.py: status as a word beside the dot, title, owner and date, one points number.
function doNextRows(list, nl, limit){
  if (!list.length) return '<div class="small sub">No open actions. The next run adds some from the biggest gaps.</div>';
  return (limit ? list.slice(0, limit) : list).map(q => { const a = q.a, tag = pathTag(q, nl);
    return `<div class="dn" tabindex="0" data-act="${esc(a.id)}"><span class="status-dot ${esc(a.status)}"></span><div style="flex:1;min-width:0"><div class="dn-t">${esc(a.title)}</div><div class="tiny sub">${stName(a.status)}${q.on ? "" : ", switched off"} · ${esc(a.owner)} · ${a.dated ? "by " + esc(shortDate(a.date)) : "no target date yet"}${tag ? ` · <span class="dn-tag">${esc(tag)}</span>` : ""}</div></div><div class="dn-p">${points(q) || "credibility"}</div></div>`; }).join("");
}
const doNextSub = nl => nl.top ? "Expected points each action adds to your best fit on its own, counting its chance."
  : `Expected points toward Level ${nl.nextLevel}, each action on its own. The path to Level ${nl.nextLevel} comes first.`;

// Each scored day's level for the journey the organisation selector follows.
function levelHist(){
  let prev = null; const out = [];
  D.runs.forEach(rn => { const v = state.org === "best" ? rn.top : rn.orgs[state.org]; if (v == null) return;
    const lv = bandIdx(v); out.push({date: rn.date, fit: v, level: lv + 1, band: BANDS[lv], change: prev == null || lv === prev ? null : lv > prev ? "up" : "down", from: prev}); prev = lv; });
  return out;
}
const lastChange = () => levelHist().filter(h => h.change).pop();
function tellText(a){ return `Mark action ${a.id} done ("${a.title}"). Evidence: <paste a link, file path or email reference>. Done when: ${a.done_when || "see the plan"}`; }
async function copyText(t){
  try { if (navigator.clipboard && navigator.clipboard.writeText){ await navigator.clipboard.writeText(t); return true; } } catch (e) {}
  try { const ta = document.createElement("textarea"); ta.value = t; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select(); const ok = document.execCommand("copy"); ta.remove(); return ok; } catch (e) { return false; }
}
// "Pending, tell your agent" ticks: this viewer's device only, never counted, never sent anywhere.
// Ticks saved under the old name (before Climb became LVLme) are still read.
const PEND_KEY = "lvlme-pending:" + D.meta.title, PEND_OLD = "climb-pending:" + D.meta.title;
let pending = new Set();
try { const v = JSON.parse(localStorage.getItem(PEND_KEY) || localStorage.getItem(PEND_OLD) || "[]"); if (Array.isArray(v)) pending = new Set(v.filter(id => D.actions.some(a => a.id === id && live(a)))); } catch (e) {}
function savePending(){ try { localStorage.setItem(PEND_KEY, JSON.stringify([...pending])); } catch (e) {} }
function goLevel(){ state.view = "level"; renderViewSeg(); showView(); $(".views-nav").scrollIntoView({behavior: motionOK() ? "smooth" : "auto", block: "start"}); }

// ---------- level up: rendering ----------
function nlLine(nl){
  if (nl.top) return "Top level. Keep the evidence fresh so it stays there.";
  if (nl.reachable){ const n = nl.set.ids.length;
    return `Level ${nl.nextLevel} expected ${nl.set.date === TODAY ? "today" : "by " + shortDate(nl.set.date)} if ${n === 1 ? "1 action lands" : n + " actions land"} on time.`; }
  return `Level ${nl.nextLevel} isn't reached on the current plan: ${fmtP(nl.missing.points)} points short, counting each action's chance.`;
}
function levelCardHTML(nl){
  const lv = nl.level - 1, lo = THRESH[lv], hi = THRESH[lv + 1];
  const pct = Math.max(0, Math.min(100, (nl.fit - lo) / (hi - lo) * 100)), ch = lastChange();
  return `<div class="level-top"><div class="level-badge${ch && ch.change === "up" && ch.date === TODAY ? " lvl-pop" : ""}">${nl.level}</div><div><div class="level-name">Level ${nl.level}, ${esc(nl.band)}</div>
    <div class="tiny sub">${nl.top ? "Top level" : `${fmtP(nl.toNext)} ${nl.toNext === 1 ? "point" : "points"} to Level ${nl.nextLevel}, ${esc(nl.nextBand)}`}</div></div></div>
    <div class="prog"><span style="width:${pct}%"></span></div>
    <div class="tiny lv-line">${esc(nlLine(nl))}</div>
    ${ch ? `<div class="tiny sub" style="margin-top:2px">${ch.change === "up" ? "Levelled up" : "Dropped a level"} ${esc(fmtDate(ch.date))}, ${esc(BANDS[ch.from])} to ${esc(ch.band)}</div>` : ""}
    <button class="linkbtn" data-go-level="1">See your quests ›</button>`;
}
const actOf = id => D.actions.find(a => a.id === id);
function stepRows(acts){
  return `<div class="lv-set">${acts.map(a => `<div class="lv-step" tabindex="0" data-act="${esc(a.id)}"><span class="lv-step-t">${esc(a.title)}</span><span class="tiny sub">${a.dated ? "by " + esc(shortDate(a.date)) : "no date yet"} · ${pctOf(a.p)}% chance</span></div>`).join("")}</div>`;
}
function lvTrack(nl){
  const idx = nl.level - 1, lo = THRESH[idx], T = nl.target, hi = THRESH[idx + 2];
  const at = v => Math.max(0, Math.min(100, (v - lo) / (hi - lo) * 100));
  const now = at(nl.fit), ex = at(nl.plan.exp), be = at(nl.plan.best), g = at(T);
  return `<div class="lv-track" role="img" aria-label="Today ${fmtP(nl.fit)}. Expected with the plan ${fmtP(nl.plan.exp)}. Best case ${fmtP(nl.plan.best)}. Level ${nl.nextLevel} starts at ${T}.">
      <div class="lv-zone" style="left:${g}%"></div><div class="lv-base"></div><div class="lv-fill" style="width:${now}%"></div>
      <div class="lv-exp" style="left:${now}%;width:${Math.max(0, ex - now)}%"></div><div class="lv-bx" style="left:${ex}%;width:${Math.max(0, be - ex)}%"></div>
      <div class="lv-goal" style="left:${g}%"></div><span class="lv-mk best" style="left:${be}%"></span><span class="lv-mk exp" style="left:${ex}%"></span><span class="lv-mk now" style="left:${now}%"></span></div>
    <div class="lv-axis"><span style="left:0;transform:none">${lo}</span><span class="goal" style="left:${g}%">Level ${nl.nextLevel} at ${T}</span><span style="left:100%;transform:translateX(-100%)">${hi}</span></div>
    <div class="legend lv-legend"><span><i class="p90-key" style="background:var(--ink)"></i>Today ${fmtP(nl.fit)}</span><span><i class="lv-key exp"></i>Expected with the plan ${fmtP(nl.plan.exp)}</span><span><i class="lv-key best"></i>Best case ${fmtP(nl.plan.best)}</span></div>`;
}
function chanceLine(set, lead){
  if (set.chance == null) return "";
  const n = set.acts.length;
  return `<p class="small sub">${lead}${pctOf(set.chance)}%${n > 1 ? ", treating each action's chance as independent" : ""}.</p>`;
}
const roleName = r => `<b>${esc(r.title)}</b> (${esc(r.on)})`;
function verdictHTML(nl){
  if (nl.top) return `<div class="lv-verdict"><div class="lv-v-h">Top level</div><p class="small">Strong is the highest band. The work now is keeping the evidence fresh and the warm paths warm.</p></div>`;
  const L = `Level ${nl.nextLevel} (${esc(nl.nextBand)})`;
  if (nl.reachable){
    const s = nl.set, n = s.acts.length, one = n === 1;
    const how = s.role === nl.r ? `, at a fit of ${fmtP(s.fit)} counting each action's chance of working.`
      : ` by lifting your fit for ${roleName(s.role)} from ${fmtP(s.role.fit)} to ${fmtP(s.fit)}, counting each action's chance of working. That role would then be your best.`;
    return `<div class="lv-verdict"><div class="lv-v-h">${one ? "One action" : n + " actions"} can get you there</div>
      <p class="small">If ${one ? "it lands on its target date" : "they land on their target dates"}, you're expected to reach ${L} on <b>${esc(fmtDate(s.date))}</b>${how}</p>
      ${chanceLine(s, "Chance it really happens: ")}
      ${nl.plan.date && nl.plan.date < s.date ? `<p class="small sub">Doing everything switched on in the plan is expected to get there sooner, on ${esc(fmtDate(nl.plan.date))}.</p>` : ""}
      ${s.exact ? "" : `<p class="small sub">The plan is long, so this set comes from a quick search; a smaller one may exist.</p>`}
      ${stepRows(s.acts)}</div>`;
  }
  const m = nl.missing, bc = nl.bestCase, same = m.r === nl.r, who = same ? "this role" : roleName(m.r);
  const room = m.room.map(x => `<div class="lv-room"><span><b style="font-weight:600">${esc(D.dimNames[x.dim])}</b><div class="tiny sub">${x.covered ? "Open actions cover part of it" : "No open action raises it for this role"}</div></span><b class="num">+${fmtP(x.points)}</b></div>`).join("");
  return `<div class="lv-verdict"><div class="lv-v-h">Not reachable on the current plan</div>
    <p class="small">Counting each action's chance of working, no set of your switched-on actions reaches ${L}. All of them together are expected to take ${same ? "this role" : `your best fit, on ${roleName(m.r)},`} to ${fmtP(nl.plan.exp)}, which is <b>${fmtP(m.points)} points short</b>.</p>
    ${bc ? `<p class="small"><b>Best case only:</b> ${bc.acts.length === 1 ? "the action below" : `the ${bc.acts.length} actions below together`} ${bc.role === nl.r ? `reach${bc.acts.length === 1 ? "es" : ""} ${fmtP(bc.fit)}` : `lift${bc.acts.length === 1 ? "s" : ""} ${roleName(bc.role)} from ${fmtP(bc.role.fit)} to ${fmtP(bc.fit)}`} by ${esc(fmtDate(bc.date))}, but only if ${bc.acts.length === 1 ? "it works" : bc.acts.length === 2 ? "both work" : "all of them work"}.</p>${chanceLine(bc, "Chance of that: ")}${stepRows(bc.acts)}`
      : `<p class="small sub">Not even the best case gets there: if every action works, your best fit reaches ${fmtP(nl.plan.best)}.</p>`}
    <div class="eyebrow" style="margin-top:16px">What is missing</div>
    ${m.ceiling < nl.target ? `<p class="small">Even with every factor at the most the plan's caps allow, ${who} tops out at ${fmtP(m.ceiling)}. Reaching ${L} needs something the caps rule out within this plan, such as more years in a similar role, or a different role.</p>`
      : `<p class="small sub">Room left on ${same ? who : who + ", the role the plan takes closest,"} within the plan's caps, in fit points, if new actions fully work. The ${fmtP(m.points)} points have to come from here: add an action where none exists, or raise the odds of the ones you have.</p>`}
    <div>${room || '<div class="small sub">No room left within the caps.</div>'}</div></div>`;
}
// What a quest card says when the action alone adds nothing to the best fit.
function noPoints(q, nl){
  const toward = nl.top ? "to your best fit" : `toward Level ${nl.nextLevel}`;
  return q.crit || (q.bc && !nl.reachable) ? `No points ${toward} on its own; it counts together with the others in the set` : `No points ${toward} on its own`;
}
// The second line of a quest card when the action carries the level through a role other than today's best.
function viaLine(q, nl){
  if (q.r === nl.r || q.exp <= 0) return "";
  return `<div class="tiny sub q-via">Lifts ${roleName(q.r)} from ${fmtP(q.r.fit)} to ${fmtP(q.fitAfter)}, which would then be your best role.</div>`;
}
function questIntro(nl){
  if (nl.top) return "Your open actions, in the same order as Do next, most points per hour first. Points are what each action on its own adds to your best fit, counting its chance of working.";
  return `Your open actions, in the same order as Do next: the ones on the path to Level ${nl.nextLevel} first, then the most points per hour. Points are what each action on its own adds to your best fit toward Level ${nl.nextLevel}, counting its chance of working. Actions that raise the same factor overlap, so their points don't simply add up; the panel above shows what they do together.`;
}
function questCard(q, nl){
  const a = q.a, pend = pending.has(a.id), tag = pathTag(q, nl);
  const tags = [tag ? `<span class="tag${q.crit ? " crit" : ""}">${esc(tag)}</span>` : "",
    pend ? '<span class="tag pend">Pending: tell your agent</span>' : "", q.on ? "" : '<span class="tag">Switched off in What if</span>',
    a.derived ? '<span class="tag">Estimated effect</span>' : "", a.stale ? `<span class="tag pend">No movement in ${a.stale} runs</span>` : ""].join("");
  const pts = !a.effects.length ? '<span class="small sub">Protects credibility, no score change</span>'
    : q.exp <= 0 && q.works <= 0 ? `<span class="small sub">${noPoints(q, nl)}</span>`
    : `<span><b class="num">${points(q)}</b> <span class="tiny sub">expected</span></span>`;
  return `<div class="quest${q.crit ? " crit" : ""}">
    <div class="q-top"><div class="q-tags">${tags}</div><span class="q-id"><span class="status-dot ${esc(a.status)}"></span>${stName(a.status)}</span></div>
    <div class="q-title" tabindex="0" data-act="${esc(a.id)}">${esc(a.title)}</div>
    <div class="q-pts">${pts}</div>${viaLine(q, nl)}
    <div class="q-meta">${esc(a.owner)}${a.effort ? " · " + esc(a.effort) : ""} · ${a.dated ? "due " + esc(fmtDate(a.date)) : "no due date yet"} · ${pctOf(a.p)}% chance</div>
    <div class="small"><span class="sub">Done when:</span> ${esc(a.done_when)}</div>
    <div class="q-foot"><button class="btn" data-tell="${esc(a.id)}">Done? Tell your agent</button>
      <label class="pend-box"><input type="checkbox" data-pend="${esc(a.id)}"${pend ? " checked" : ""}> Pending on this device</label></div>
    <div class="q-msg" role="status"></div></div>`;
}
function progressHTML(){
  const days = D.progress || [], n = D.streak || 0, hist = levelHist().slice().reverse(), dayOf = {};
  days.forEach(d => dayOf[d.date] = d);
  const why = d => !d ? "" : d.start ? "Day 1, measured." : !d.progress ? "No real progress that day." :
    cap1([d.roles_up ? `fit rose on ${plural(d.roles_up, "role")}` : "", d.evidence.length ? `newly checked evidence (${plural(d.evidence.length, "item")})` : "",
      d.actions.length ? `${plural(d.actions.length, "action")} done with evidence` : ""].filter(Boolean).join(" · ")) + ".";
  const who = state.org === "best" ? "your best role" : esc(D.orgs[state.org].name) + "'s best role";
  return `<h2 class="eyebrow">Progress you can trust</h2>
    <div class="streak"><div class="streak-n num${n ? "" : " zero"}">${n}</div><div><div style="font-weight:650">${n === 1 ? "scored day" : "scored days"} in a row with real progress</div>
      <div class="tiny sub">${days.length < 2 ? "Day 1 is measured. The streak starts with the next scored day that shows real progress." : !n ? "The latest scored day showed no real progress, so the streak starts again." : "Real progress means a score that rose, newly checked evidence, or an action done with evidence, on any role."}</div></div></div>
    <div class="streak-dots" aria-hidden="true">${days.map(d => `<span class="sd${d.start ? " start" : d.progress ? " on" : ""}" title="${esc(fmtDate(d.date))}: ${esc(why(d))}"></span>`).join("")}</div>
    <h3 class="eyebrow" style="margin-top:16px">Level history, ${who}</h3>
    <div class="tiny sub" style="margin-bottom:4px">One row per scored day, newest first, from the dated files in eval/runs.</div>
    <div>${hist.map(h => `<div class="lh-row"><span class="tiny sub lh-date">${esc(fmtDate(h.date))}</span><span class="lv-badge">${h.level}</span>
      <div><div class="small"><b>Level ${h.level}, ${esc(h.band)}</b> · fit ${Math.round(h.fit)}${h.change ? ` <span class="tag ${h.change}">${h.change === "up" ? "Level up" : "Level down"}</span>` : ""}</div>
      <div class="tiny sub">${esc(why(dayOf[h.date]))}</div></div></div>`).join("")}</div>`;
}
function renderLevel(){
  const {rs, nl, up} = lv(), r = rs[0], qs = up;           // the quests in the Do next order
  const who = state.org === "best" ? "Your best role" : esc(D.orgs[state.org].name) + ", best role";
  $("#v-level").innerHTML = `<div class="card lv-card"><div class="lv-head"><div><h2 class="eyebrow">Next level · ${who}</h2>
      <h3>Level ${nl.level}, ${esc(nl.band)}${nl.top ? "" : ` <span class="arrow">→</span> Level ${nl.nextLevel}, ${esc(nl.nextBand)}`}</h3><div class="small sub">${esc(r.on)}: ${esc(r.title)}</div></div>
      ${nl.top ? "" : `<div class="lv-need"><b class="num">${fmtP(nl.toNext)}</b><span class="tiny sub">points to go</span></div>`}</div>
      ${nl.top ? "" : lvTrack(nl)}${verdictHTML(nl)}</div>
    <h2 class="eyebrow" style="margin:22px 4px 4px">Quests${nl.top ? "" : ` toward Level ${nl.nextLevel}`}</h2>
    <p class="small" style="margin:0 4px 12px">${esc(questIntro(nl))} Ticks stay on this device and never change a number; your plan file is the record, so tell your agent.</p>
    ${qs.length ? `<div class="quests">${qs.map(q => questCard(q, nl)).join("")}</div>` : '<div class="card small sub">No open actions. The next run adds some from the biggest gaps.</div>'}
    <div class="card" style="margin-top:16px">${progressHTML()}</div>`;
  bindLevel($("#v-level"));
}
function bindLevel(root){
  root.querySelectorAll("[data-act]").forEach(n => onEnter(n, () => openDetail({type: "action", id: n.dataset.act}, true)));
  root.querySelectorAll("[data-tell]").forEach(b => b.addEventListener("click", () => tellAgent(b)));
  root.querySelectorAll("[data-pend]").forEach(c => c.addEventListener("change", () => {
    const id = c.dataset.pend; if (c.checked) pending.add(id); else pending.delete(id); savePending();
    renderLevel(); const again = $(`#v-level [data-pend="${id}"]`); if (again) again.focus();
  }));
}
async function tellAgent(b){
  const a = actOf(b.dataset.tell), text = tellText(a), msg = b.closest(".quest, .d-body").querySelector(".q-msg");
  const ok = await copyText(text);
  msg.innerHTML = ok ? "Copied. Paste it to your agent and add the evidence." : `Copy this to your agent:<span class="q-text">${esc(text)}</span>`;
  if (ok){ b.textContent = "Copied"; setTimeout(() => { b.textContent = "Done? Tell your agent"; }, 2400); }
}
"""

JS_DETAIL = r"""
// ---------- detail pane ----------
const detail = $("#detail"), scrim = $("#scrim");
const narrow = () => matchMedia("(max-width:1279px)").matches;
function crumbLabel(n){ return n.type === "org" ? D.orgs[n.id].name : n.type === "role" ? ((roleById[n.id] || {}).title || "Role") : n.type === "factor" ? D.dimNames[DIMS[n.k]] : n.type === "evidence" ? n.id : "Action"; }
function openDetail(node, reset){
  if (reset){ state.stack = []; if (node.type === "role"){ const r = roleById[node.id]; if (r && D.orgs[r.g]) state.stack.push({type: "org", id: r.g}); } }
  state.stack.push(node); renderDetail();
  detail.classList.add("slide"); detail.classList.add("open"); if (narrow()) scrim.classList.add("on");
}
function closeDetail(){ state.stack = []; detail.classList.remove("open"); if (!narrow()) renderHome(); if (!$("#rail").classList.contains("open") && !$("#modal").classList.contains("on")) scrim.classList.remove("on"); }
function renderDetail(){
  const node = state.stack[state.stack.length - 1];
  const home = narrow() ? "" : '<button data-home="1">Start here</button><span class="sep">›</span>';
  const crumbs = home + state.stack.map((n, i) => `${i ? '<span class="sep">›</span>' : ""}<button data-i="${i}">${esc(crumbLabel(n))}</button>`).join("");
  const body = node.type === "org" ? detailOrg(node.id) : node.type === "role" ? detailRole(node.id) : node.type === "factor" ? detailFactor(node.id, node.k) : node.type === "evidence" ? detailEvidence(node.id) : detailAction(node.id);
  const card = $("#detailCard");
  card.innerHTML = `<div class="d-head"><div class="crumbs">${crumbs}</div><button class="close" aria-label="Close details">✕</button></div><div class="d-body">${body}</div>`;
  card.querySelector(".close").addEventListener("click", closeDetail);
  card.querySelectorAll(".crumbs [data-home]").forEach(b => b.addEventListener("click", closeDetail));
  card.querySelectorAll(".crumbs button[data-i]").forEach(b => b.addEventListener("click", () => { state.stack = state.stack.slice(0, +b.dataset.i + 1); renderDetail(); }));
  card.querySelectorAll("[data-factor]").forEach(f => f.addEventListener("click", () => { state.stack.push({type: "factor", id: f.dataset.role, k: +f.dataset.factor}); renderDetail(); }));
  card.querySelectorAll("[data-role-open]").forEach(n => n.addEventListener("click", () => { state.stack.push({type: "role", id: n.dataset.roleOpen}); renderDetail(); }));
  card.querySelectorAll("[data-tell]").forEach(b => b.addEventListener("click", () => tellAgent(b)));
  bindChips(card); enter(card, 700); detail.scrollTop = 0;
}
function detailOrg(g){
  const L = D.orgs[g], r = roleById[L.best], exp = P[r.id].exp, best = P[r.id].best, nj = L.count - L.judged;
  const net = L.members.length > 1 ? "Several organisations share this colour; open one of its roles for its warm path." :
    [L.network || "No known contact yet.", L.first != null ? plural(L.first, "first-degree contact") + " from your network map." : ""].filter(Boolean).join(" ");
  return `<h2><i class="org-key" style="background:${orgColour(g)};margin-right:8px"></i>${esc(L.name)}</h2>
    ${L.judged ? `<div class="journey-mini"><b>${Math.round(r.fit)}</b><span class="arrow">→</span><b>${Math.round(exp.end)}</b><span class="arrow">→</span><b>${Math.round(best.end)}</b></div>
    <div class="tiny sub">best role today, expected, best case</div>` : `<div class="small warnline">No role judged yet at ${esc(L.name)}, so there is no best role or fit to show. The next run can judge them.</div>`}
    <div class="kv" style="margin-top:10px"><span>Roles matching your types</span><b class="num">${L.count}</b></div>
    <div class="kv"><span>With an eligibility blocker</span><b class="num">${L.blocked}</b></div>
    <div class="kv"><span>Judged so far</span><b class="num">${L.judged} of ${L.count}</b></div>
    <div class="eyebrow" style="margin-top:16px">Who knows you here</div><div class="small">${esc(net)}</div>
    ${L.paths.map(p => `<div class="small sub" style="margin-top:6px"><span class="tag">${esc(cap1(p.status))}</span> ${esc(p.note)}</div>`).join("")}
    ${warmDetail(L)}
    ${L.judged ? `<div class="eyebrow" style="margin-top:16px">Best roles</div>` : ""}
    ${D.roles.filter(x => x.g === g && x.judged).slice(0, 10).map(x => `<div class="row" style="padding:10px 0" data-role-open="${esc(x.id)}"><div class="row-main"><div class="small" style="font-weight:600">${esc(x.title)}</div><div class="tiny sub">${esc(x.loc.slice(0, 2).join(", "))}${x.blocked ? " · eligibility blocker" : ""}</div></div><div class="row-side"><b>${Math.round(fitM(x))}</b></div><span class="chev">›</span></div>`).join("")}
    ${nj ? `<div class="tiny sub" style="margin-top:8px">${esc(plural(nj, "role"))} not judged yet: see them in Roles.</div>` : ""}`;
}
function raisingActions(r, k){ if (CAPS[k] === 0 || hardBlock(r, k)) return []; return D.actions.filter(a => enabled.has(a.id) && switchable(a) && a.effects.some(e => e.dimension === DIMS[k] && inScope(r, e.scope || {}))); }
function dotRow(score, proj){ let s = ""; for (let i = 1; i <= 5; i++){ const on = i <= Math.round(score), pj = !on && i <= Math.round(proj); s += `<i class="${on ? "on" : pj ? "proj" : ""}"></i>`; } return `<span class="dots" aria-label="${score} of 5">${s}</span>`; }
function detailRole(id){
  const r = roleById[id], exp = P[r.id].exp, best = P[r.id].best;
  const block = r.hard ? `This role has an eligibility blocker you can't clear${r.bt ? " (" + r.bt + ")" : ""}, so eligibility stays at zero.`
    : r.blocked ? `This role has an eligibility blocker${r.bt ? " (" + r.bt + ")" : ""}. Eligibility rises only if a plan action clears it.` : "";
  return `<h2>${esc(r.title)}</h2><div class="small sub">${esc(r.on)} · ${esc(D.families[r.family] || "")} · ${esc(r.loc.join(", "))}</div>
    <div class="journey-mini"><b>${Math.round(r.fit)}</b><span class="arrow">→</span><b>${Math.round(exp.end)}</b><span class="arrow">→</span><b>${Math.round(best.end)}</b></div><div class="tiny sub">today, expected, best case</div>
    <div class="kv" style="margin-top:8px"><span>Interview chance now</span>${pill(r.ib)}</div><div class="kv"><span>Offer chance now</span>${pill(r.ob)}</div>
    <div class="kv"><span>If the plan works</span>${pill(interviewBand(exp.end, exp.scores, r.hrl))}</div>
    ${block ? `<div class="small warnline">${esc(block)}</div>` : ""}
    ${!r.judged ? '<div class="small warnline">Not judged yet: requirements match, proof of work and the organisation edge count as 0 until the next run judges it.</div>' : ""}
    ${r.awaiting.length ? `<div class="small sub" style="margin-top:8px">Waiting for the reviewer: ${esc(r.awaiting.map(d => D.dimNames[d]).join(", "))}. Each counts as 2 until reviewed.</div>` : ""}
    ${r.rn ? `<div class="small" style="margin-top:10px"><b>Reviewer:</b> ${esc(r.rn)}</div>` : ""}
    <div class="eyebrow" style="margin-top:16px">The seven factors, tap one to drill in</div>
    <div class="tiny sub" style="margin-bottom:4px">Filled dots: today. Green rings: where the plan is expected to take you.</div>
    ${DIMS.map((d, k) => `<div class="factor" data-factor="${k}" data-role="${esc(r.id)}"><div class="factor-top"><span class="factor-name">${esc(D.dimNames[d])} <span class="tiny sub">weight ${W[k]}</span></span>${dotRow(r.s[k], exp.scores[k])}</div><div class="tiny sub">${esc(r.n[k])}</div></div>`).join("")}
    ${r.adj.length ? `<div class="eyebrow" style="margin-top:16px">Adjustments</div><ul class="small">${r.adj.map(h => `<li>${esc(h)}</li>`).join("")}</ul>` : ""}
    ${r.hardReq.length ? `<div class="eyebrow" style="margin-top:16px">What the posting requires</div><ul class="small">${r.hardReq.map(h => `<li>${esc(h)}</li>`).join("")}</ul>` : ""}
    ${r.url ? `<p class="small"><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">Open the job posting</a></p>` : ""}`;
}
function detailFactor(id, k){
  const r = roleById[id], exp = P[r.id].exp, acts = raisingActions(r, k);
  const why = CAPS[k] === 0 ? "The plan can't move this factor within the projection (its cap is 0)." : hardBlock(r, k) ? "A blocker you can't clear keeps this at zero." : "No open action in the plan raises this factor for this role yet.";
  return `<h2>${esc(D.dimNames[DIMS[k]])}</h2><div class="small sub">${esc(D.dimHelp[DIMS[k]])}</div>
    <div class="kv" style="margin-top:12px"><span>Score for this role</span><span>${dotRow(r.s[k], exp.scores[k])} <b class="num">${r.s[k]}</b>/5</span></div>
    <div class="kv"><span>Weight</span><b class="num">${W[k]} of ${TW}</b></div>
    <div class="kv"><span>Most the plan can add</span><b class="num">${CAPS[k]}</b></div>
    <div class="eyebrow" style="margin-top:14px">Why</div><div class="small">${esc(r.n[k]) || "No note."}</div>
    <div class="eyebrow" style="margin-top:14px">Evidence behind it</div><div>${r.e[k].length ? r.e[k].map(evChip).join("") : '<span class="small sub">None yet.</span>'}</div>
    <div class="eyebrow" style="margin-top:14px">Actions that raise it</div><div>${acts.length ? acts.map(a => actChip(a.id)).join("") : `<span class="small sub">${esc(why)}</span>`}</div>`;
}
function detailEvidence(id){
  const e = D.evidence.find(x => x.id === id); if (!e) return `<p class="sub">Evidence ${esc(id)} not found.</p>`;
  const users = D.roles.filter(r => r.e.some(list => list.indexOf(id) >= 0));
  return `<div class="tiny sub">${esc(e.id)} · ${esc(cap1(e.cat.replace(/_/g, " ")))}</div><h3 style="margin-top:4px">${esc(e.claim)}</h3><span class="tag t-${esc(e.status)}">${esc(levelName(e.status))}</span>
    <div class="eyebrow" style="margin-top:14px">Sources</div>${e.sources.length ? e.sources.map(s => `<div class="small" style="margin-top:4px">${esc(cap1(s.type))}: ${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.ref)}</a>` : esc(s.ref)}${s.note ? `<div class="tiny sub">${esc(s.note)}</div>` : ""}${s.checked ? `<div class="tiny sub">Checked ${esc(fmtDate(s.checked))}</div>` : ""}</div>`).join("") : '<div class="small sub">No source yet, so it counts as 0.</div>'}
    ${e.notes ? `<div class="eyebrow" style="margin-top:14px">Notes</div><div class="small">${esc(e.notes)}</div>` : ""}
    ${e.dims.length ? `<div class="eyebrow" style="margin-top:14px">Feeds</div><div class="small">${esc(e.dims.map(d => D.dimNames[d]).join(", "))}</div>` : ""}
    <div class="eyebrow" style="margin-top:14px">Cited by</div><div class="small sub">${plural(users.length, "role")}</div>
    ${users.slice(0, 6).map(r => `<div class="row" style="padding:8px 0" data-role-open="${esc(r.id)}"><div class="row-main small">${esc(r.title)} <span class="sub">· ${esc(r.on)}</span></div><b>${Math.round(r.fit)}</b><span class="chev">›</span></div>`).join("")}`;
}
function effectText(e){
  const sc = e.scope || {}, where = [];
  if (sc.orgs && sc.orgs.length) where.push(sc.orgs.map(o => D.orgNames[o] || o).join(" and "));
  if (sc.families && sc.families.length) where.push(sc.families.map(f => D.families[f] || f).join(", ") + " roles");
  if (sc.location_classes && sc.location_classes.length) where.push(sc.location_classes.map(l => D.locations[l] || l).join(", "));
  if (sc.role_ids && sc.role_ids.length) where.push(plural(sc.role_ids.length, "named role"));
  const by = ("delta" in e) ? "+" + r1(e.delta) : "to at least " + e.set_at_least;
  return `${D.dimNames[e.dimension] || e.dimension} ${by}${where.length ? " for " + where.join(", ") : " for every role"}`;
}
// The action pane: the same points number as the action's Do next row and quest card, then the detail behind it.
function actionPoints(a){
  const L = lv(), nl = L.nl, q = L.qs.find(x => x.a.id === a.id), lbl = nl.top ? "Adds to your best fit" : `Toward Level ${nl.nextLevel}, expected`;
  if (a.status === "done") return `<div class="kv"><span>${lbl}</span><b class="num">Already in today's scores</b></div>`;
  if (!q) return a.status === "later" ? `<div class="kv"><span>${lbl}</span><span>Switch it on in What if to count it</span></div>` : "";
  if (!a.effects.length) return `<div class="kv"><span>${lbl}</span><span>Protects credibility, no score change</span></div>`;
  return `<div class="kv"><span>${lbl}</span><b class="num" style="color:var(--ok)">${points(q)}</b></div>
    <div class="kv"><span>If it works</span><b class="num">+${fmtP(Math.max(0, q.works))}</b></div>
    ${a.hours ? `<div class="kv"><span>Per hour of effort</span><b class="num">${fmtP(q.rate)}</b></div>` : ""}
    ${q.r !== nl.r && q.exp > 0 ? `<div class="small sub" style="margin:4px 0">Lifts ${roleName(q.r)} from ${fmtP(q.r.fit)} to ${fmtP(q.fitAfter)}, which would then be your best role. On your best role today: ${q.leadExp > 0 ? "+" + fmtP(q.leadExp) + " expected" : "no change"}.</div>` : ""}`;
}
function detailAction(id){
  const a = D.actions.find(x => x.id === id);
  const affected = D.roles.filter(x => a.effects.some(e => inScope(x, e.scope || {}))).length;
  return `<div class="tiny sub">${esc(a.id)} · ${stName(a.status)}</div><h2>${esc(a.title)}</h2>${a.why ? `<p class="small">${esc(a.why)}</p>` : ""}
    ${a.stale ? `<div class="small warnline">No score or metric movement in ${a.stale} runs: rework it or drop it.</div>` : ""}
    <div class="kv"><span>Owner</span><span>${esc(a.owner)}</span></div>${a.effort ? `<div class="kv"><span>Effort</span><span>${esc(a.effort)}</span></div>` : ""}
    <div class="kv"><span>${a.status === "done" ? "Done on" : "Target date"}</span><span>${a.dated || a.status === "done" ? esc(fmtDate(a.date)) : "Not set, counted at the end"}</span></div><div class="kv"><span>Chance it works</span><b class="num">${Math.round(a.p * 100)}%</b></div>
    ${actionPoints(a)}
    <div class="kv"><span>Roles it touches</span><b class="num">${affected}</b></div>
    ${a.metric ? `<div class="kv"><span>Moves the metric</span><span>${esc(a.metric)}</span></div>` : ""}
    <div class="eyebrow" style="margin-top:14px">What it changes</div>${a.effects.length ? `<ul class="small">${a.effects.map(e => `<li>${esc(effectText(e))}</li>`).join("")}</ul>${a.derived ? '<div class="tiny sub">Estimated from its expected points; the plan lists no effects for it.</div>' : ""}` : '<div class="small sub">Protects credibility. No direct score change.</div>'}
    <div class="eyebrow" style="margin-top:14px">Done when</div><div class="small">${esc(a.done_when)}</div>
    ${a.doneEvidence ? `<div class="eyebrow" style="margin-top:14px">Proof it's done</div><div class="small">${esc(a.doneEvidence)}</div>` : ""}
    ${a.draft ? `<div class="eyebrow" style="margin-top:14px">Draft ready for you</div><div class="small">${esc(a.draft)}, for you to read, edit and send yourself.</div>` : ""}
    ${a.notes ? `<div class="eyebrow" style="margin-top:14px">Notes</div><div class="small">${esc(a.notes)}</div>` : ""}
    ${live(a) ? `<div style="margin-top:16px"><button class="btn" data-tell="${esc(a.id)}">Done? Tell your agent</button><div class="q-msg" role="status" style="margin-top:6px"></div><div class="tiny sub" style="margin-top:6px">Copies an instruction for your agent. The plan file is the record: nothing here changes until your agent marks it done there, with evidence.</div></div>` : ""}`;
}

// ---------- share card ----------
const modal = $("#modal");
function shareNumbers(){ const r = D.roles[0], e = jp("best").exp, d1 = D.runs[0] || {top: r.fit, ib: r.ib};
  return {r, d1: d1.top, d1b: d1.ib, exp: e.end, eb: interviewBand(e.end, e.scores, e.r.hrl),
          head: shareHeadline(d1.top, r.fit, Math.round((tOf(TODAY) - tOf(D.meta.baseline)) / 864e5) + 1)}; }
// The share headline states only what was measured: the flight level on day 1 and today, counted in days
// like the Day number above the chart. It never claims an offer: the card is built to be shared, so it must
// stay as honest as the dashboard.
function shareHeadline(d1, now, day){
  const lv = v => "Level " + (bandIdx(v) + 1) + ", " + BANDS[bandIdx(v)];
  if (day <= 1) return lv(now) + " on day 1";
  return bandIdx(d1) === bandIdx(now) ? lv(now) + " on day 1 and day " + day : lv(d1) + " to " + lv(now) + " by day " + day;
}
function openShare(){
  const s = shareNumbers();
  $("#shareCard").innerHTML = `<div class="eyebrow">Dream job journey</div><h3 style="font-size:20px">${esc(s.head)}</h3>
    <div class="small sub">Measured, dated and checkable. Day 1: <span style="white-space:nowrap">${esc(fmtDate(D.meta.baseline))}</span>.</div>
    <div class="share-row"><div><span class="tiny sub">Day 1</span><b class="num">${Math.round(s.d1)}</b>${pill(s.d1b)}</div><div><span class="tiny sub">Today</span><b class="num">${Math.round(s.r.fit)}</b>${pill(s.r.ib)}</div><div><span class="tiny sub">Projected</span><b class="num">${Math.round(s.exp)}</b>${pill(s.eb)}</div></div>
    <div class="tiny sub" style="margin-top:8px">Fit out of 100, interview chance under it. Projection assumes the plan is followed.</div>`;
  modal.classList.add("on"); scrim.classList.add("on");
}
function closeShare(){ modal.classList.remove("on"); if (!detail.classList.contains("open") && !$("#rail").classList.contains("open")) scrim.classList.remove("on"); }
function saveImage(){
  const s = shareNumbers(), cv = document.createElement("canvas"); cv.width = 1200; cv.height = 630; const x = cv.getContext("2d"), F = "-apple-system,Helvetica,Arial";
  x.fillStyle = "#f6f8fc"; x.fillRect(0, 0, 1200, 630);
  x.fillStyle = "#56565b"; x.font = "650 26px " + F; x.fillText("DREAM JOB JOURNEY", 70, 100);
  x.fillStyle = "#1d1d1f"; let hs = 54; do { x.font = "700 " + hs + "px " + F; } while (x.measureText(s.head).width > 1060 && --hs > 30); x.fillText(s.head, 70, 170);
  x.fillStyle = "#56565b"; x.font = "400 28px " + F; x.fillText("Measured, dated and checkable. Day 1: " + fmtDate(D.meta.baseline), 70, 220);
  [["Day 1", s.d1, s.d1b], ["Today", s.r.fit, s.r.ib], ["Projected", s.exp, s.eb]].forEach((c, i) => {
    const bx = 70 + i * 360; x.fillStyle = "#ffffff"; x.fillRect(bx, 280, 330, 230);
    x.fillStyle = "#56565b"; x.font = "500 26px " + F; x.fillText(c[0], bx + 30, 330);
    x.fillStyle = "#1d1d1f"; x.font = "700 96px " + F; x.fillText(String(Math.round(c[1])), bx + 30, 435);
    x.fillStyle = "#084c9e"; x.font = "650 28px " + F; x.fillText(c[2], bx + 30, 485);
  });
  x.fillStyle = "#56565b"; x.font = "400 22px " + F; x.fillText("Fit out of 100, interview chance under it. Projection assumes the plan is followed.", 70, 575);
  const a = document.createElement("a"); a.download = "dream-job-journey.png"; a.href = cv.toDataURL("image/png"); a.click();
}

// ---------- controls ----------
function renderSegs(){
  $("#modeSeg").innerHTML = MODES.map(m => `<button aria-pressed="${state.mode === m[0]}" data-m="${m[0]}">${m[1]}</button>`).join("");
  $("#modeSeg").querySelectorAll("button").forEach(b => b.addEventListener("click", () => { state.mode = b.dataset.m; renderSegs(); refreshNumbers(); }));
  const opts = [["best", "Best overall"]].concat(D.orgOrder.filter(g => D.orgs[g].judged).map(g => [g, D.orgs[g].name]));   // no journey where nothing is judged
  $("#orgSeg").innerHTML = opts.map(o => `<button aria-pressed="${state.org === o[0]}" data-org="${esc(o[0])}">${esc(o[1])}</button>`).join("");
  // The level, Do next, the quests and the plan list all follow the selected journey.
  $("#orgSeg").querySelectorAll("button").forEach(b => b.addEventListener("click", () => { state.org = b.dataset.org; LV = null; renderSegs(); renderTopline(); drawChart(); renderHistory(); renderDoNext();
    if (state.view === "level" || state.view === "plan") showView(false); refreshDetail(); }));
  scrollHint($("#orgSeg"));
}
function renderHistory(){
  const lh = {}; levelHist().forEach(h => lh[h.date] = h);
  const what = state.org === "best" ? "best fit" : "best at " + D.orgs[state.org].name;
  $("#history").innerHTML = D.runs.map(rn => { const h = lh[rn.date];
    return `<div class="run-chip"><div class="tiny sub">${esc(fmtDate(rn.date))}${rn.date === D.runs[0].date ? " · Day 1" : ""}</div>${h ? `<b class="num">${Math.round(h.fit)}</b> <span class="tiny sub">${esc(what)}</span>
      <div class="tiny">Level ${h.level}, ${esc(h.band)}${h.change ? `<span class="tag ${h.change}">${h.change === "up" ? "Level up" : "Level down"}</span>` : ""}</div>` : '<span class="tiny sub">No open role that day</span>'}${D.meta.git ? `<div class="tiny sub">${rn.commit ? `Saved in history: <span class="num" style="color:var(--ink);font-weight:600">${esc(rn.commit)}</span>` : "Not saved in history yet"}</div>` : ""}</div>`; }).join("") +
    (state.sample ? sampleProgress(headlineRole()).map(p => `<div class="run-chip sample"><div class="tiny sub">${esc(new Date(p.t).toLocaleDateString("en-AU", {day: "numeric", month: "short"}))} · sample</div><b class="num">${Math.round(p.v)}</b></div>`).join("") : "");
  if (!state.sample){ const h = $("#history"); h.scrollLeft = h.scrollWidth; }
}
function refreshDetail(){ if (state.stack.length && (detail.classList.contains("open") || !narrow())) renderDetail(); else if (!narrow()) renderHome(); }
function refreshNumbers(){ renderTopline(); renderTiles4(); showView(false); refreshDetail(); }
function refresh(){ recompute(); renderTopline(); drawChart(); renderTiles4(); renderDoNext(); renderSwitches(); renderHistory(); showView(false); refreshDetail(); }
let theme = "light";
try { const t = localStorage.getItem("lvlme-theme") || localStorage.getItem("climb-theme"); if (t === "dark" || t === "light") theme = t; } catch (e) {}
function applyTheme(){
  if (theme === "dark") document.documentElement.dataset.theme = "dark"; else delete document.documentElement.dataset.theme;
  $("#themeSeg").querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.t === theme)));
}
$("#themeSeg").querySelectorAll("button").forEach(b => b.addEventListener("click", () => { theme = b.dataset.t; try { localStorage.setItem("lvlme-theme", theme); } catch (e) {} applyTheme(); chartBuilt = false; lastVals = null; refresh(); }));
$("#allOn").addEventListener("click", () => { D.actions.forEach(a => { if (switchable(a)) enabled.add(a.id); }); refresh(); });
$("#allOff").addEventListener("click", () => { enabled.clear(); refresh(); });
$("#sampleTog").addEventListener("click", () => { state.sample = !state.sample; $("#sampleTog").setAttribute("aria-checked", String(state.sample)); renderTopline(); drawChart(); renderHistory(); });
$("#railDone").addEventListener("click", () => { $("#rail").classList.remove("open"); if (!detail.classList.contains("open")) scrim.classList.remove("on"); });
$("#fab").addEventListener("click", () => { const r = $("#rail"); r.classList.add("slide"); r.classList.add("open"); scrim.classList.add("on"); });
scrim.addEventListener("click", () => { $("#rail").classList.remove("open"); closeDetail(); closeShare(); scrim.classList.remove("on"); });
$("#shareBtn").addEventListener("click", openShare);
$("#modalClose").addEventListener("click", closeShare);
$("#saveImg").addEventListener("click", saveImage);
function syncTop(){ document.documentElement.style.setProperty("--top-h", $(".top").offsetHeight + "px"); }
let resizeTimer;
addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => {
  syncTop();
  const w = Math.max(260, Math.round($("#chartWrap").clientWidth));
  if (w !== CW){ chartBuilt = false; lastVals = null; drawChart(); if (state.view === "plan") renderPlan(); }
  if (!narrow() && !state.stack.length) renderHome();
  scrollHint($("#viewSeg")); scrollHint($("#orgSeg"));
}, 150); });
document.addEventListener("keydown", e => { if (e.key === "Escape"){ closeShare(); closeDetail(); $("#rail").classList.remove("open"); scrim.classList.remove("on"); } });

// ---------- boot: the final state is rendered synchronously; motion is a bonus ----------
applyTheme();
$("#brandTitle").textContent = D.meta.title;
$("#storyLine").textContent = (D.meta.subtitle ? D.meta.subtitle + " " : "") + "Day 1 measured " + fmtDate(D.meta.baseline) + ". Every scored day is saved, so the climb is checkable.";
if (D.meta.fictional){ $("#banner").hidden = false; $("#bannerText").textContent = "Demo with made-up data. " + (D.meta.person || "This person") + " and every organisation, role and contact here are fictional."; }
$("#builtAt").textContent = D.meta.built;
$("#recordNote").textContent = D.meta.git
  ? "Every scored day is saved in your workspace's history. Each chip shows the saved version that first recorded that day, so the climb is a record anyone can check."
  : "Every scored day is kept as a dated file in eval/runs. Make your workspace its own git repository (with no remote) and each chip will also show the saved version that first recorded that day.";
syncTop();
if (!D.roles.length){
  $("#centre").innerHTML = '<div class="card"><h3>No open roles matched yet</h3><p class="small sub">Fetch roles and score a run, then build the dashboard again.</p></div>';
  return;
}
if (motionOK()) document.body.classList.add("animate");
document.addEventListener("visibilitychange", () => { if (document.visibilityState !== "visible") document.body.classList.remove("animate"); else if (!reduce) document.body.classList.add("animate"); });
$("#sampleRow").hidden = !(D.meta.sample_allowed && PREVIEW);     // a design preview, only with ?preview=1
recompute(); lv().up.forEach((q, i) => RANK[q.a.id] = i);
renderSegs(); renderViewSeg(); renderMetrics(); renderSwitches(); renderTopline(); drawChart(); renderTiles4(); renderDoNext(); renderHistory(); showView();
$("#staticSummary").hidden = true;   // the live page has rendered the same numbers; the static copy is for readers without JavaScript
enter($("#hero"), 1500);
})();
"""

HEADER = r"""<!doctype html>
<!--
  DESIGN LANGUAGE: Calm mission control. Base: the Apple Health look (system font,
  soft surfaces, one accent, roomy spacing, 16px and up body text), light by default
  with a readable dark switch. Hero: the flight path (altitude is fit, chance bands
  are flight levels, the measured Day 1 is the departure, plan actions are diamond
  waypoints, the offer zone is the destination) under a flight strip and a level
  badge. Left rail: the what-if switches with their own lift. Centre below the hero:
  scoreboard tiles, then the views, led by Level up (the next level, quests, level
  history and streak). Right pane: Start here (Do next, Warm paths, Biggest unlocks), then
  drill-down with breadcrumbs. One yardstick: Do next, the quests, the badges and the
  plan list share one order (the path to the next level first, then points per hour)
  and one points number per action; only the What if rail shows "with everything else
  on". On a phone Do next follows the headline status, first-screen controls are 44
  points, the tab row scrolls with a visible hint, and the rail opens from a bottom
  toolbar that reserves its own space. Motion is quiet and never leaves content hidden.
  Built by LVLme scripts/build_dashboard.py.
-->
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>__TITLE__</title>
<style>"""

TEMPLATE = (HEADER + CSS + "</style></head>\n<body>" + BODY
            + '\n<script type="application/json" id="data">__DATA__</script>\n<script>'
            + JS_CORE + JS_CHART + JS_HOME + JS_VIEWS + JS_LEVELS + JS_DETAIL + "</script>\n</body></html>\n")
