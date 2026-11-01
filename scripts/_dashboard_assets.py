"""Inline CSS and JavaScript for the dashboard (report/index.html).

Plain strings, no templating, so braces need no escaping. The page makes no
external requests: no fonts, scripts or images are loaded from anywhere.
Colours: one accent, a sequential blue ramp for the chance bands, and the
validated colour-blind-safe categorical palette for organisations.
"""

# Categorical slots (light, dark), fixed order, never cycled. Colour follows
# the organisation (its position in config.json targets).
PALETTE = [
    ("#2a78d6", "#3987e5"), ("#eb6834", "#d95926"), ("#1baf7a", "#199e70"), ("#eda100", "#c98500"),
    ("#e87ba4", "#d55181"), ("#008300", "#008300"), ("#6250d6", "#9085e9"), ("#e34948", "#e66767"),
]
OTHER = ("#8e8e93", "#8e8e93")

CSS = r"""
:root { color-scheme: light; --bg:#f5f5f7; --card:#ffffff; --ink:#1d1d1f; --sub:#6e6e73; --rule:#e5e5ea;
  --accent:#0071e3; --grid:#ececf0; --hl:#eef5ff; --up:#1f8a3b; --down:#d70015; --warn-bg:#fff4d6; --warn-ink:#6b4a00;
  --s1:#2a78d6;
  --p0:#e5e5ea; --p0t:#3a3a3c; --p1:#b7d3f6; --p1t:#0d366b; --p2:#5598e7; --p2t:#ffffff; --p3:#256abf; --p3t:#ffffff;
  --p4:#0d366b; --p4t:#ffffff; }
@media (prefers-color-scheme: dark) { :root { color-scheme: dark; --bg:#000000; --card:#1c1c1e; --ink:#f5f5f7;
  --sub:#98989d; --rule:#38383a; --accent:#2997ff; --grid:#2c2c2e; --hl:#0c2340; --up:#30d158; --down:#ff453a;
  --warn-bg:#3a2e0b; --warn-ink:#ffd60a; --s1:#3987e5; --p0:#3a3a3c; --p0t:#e5e5ea; --p1:#184f95; --p1t:#ffffff; } }
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased; overflow-wrap:break-word; }
.wrap { max-width:980px; margin:0 auto; padding:20px 16px 72px; }
h1 { font-size:30px; letter-spacing:-0.02em; margin:4px 0 2px; line-height:1.15; }
h2 { font-size:20px; margin:32px 0 12px; letter-spacing:-0.01em; }
h3 { font-size:16px; margin:0 0 8px; }
.muted { color:var(--sub); } .small { font-size:13px; } .num { font-variant-numeric:tabular-nums; }
.banner { background:var(--warn-bg); color:var(--warn-ink); border-radius:12px; padding:10px 14px; font-size:14px; margin:12px 0; }
.seg { display:grid; grid-template-columns:repeat(6,1fr); gap:2px; background:var(--rule); padding:2px; border-radius:10px;
  margin:18px 0 8px; position:sticky; top:8px; z-index:5; }
.seg a { text-align:center; padding:7px 4px; border-radius:8px; color:var(--ink); text-decoration:none; font-size:14px;
  font-weight:500; white-space:nowrap; }
.seg a.on { background:var(--card); box-shadow:0 1px 3px rgba(0,0,0,.12); }
@media (max-width:520px) { .seg { grid-template-columns:repeat(3,1fr); } }
.view-title { margin-top:40px; }
.js .view { display:none; } .js .view.on { display:block; } .js .view-title { display:none; }
.card { background:var(--card); border-radius:14px; padding:16px 18px; margin-bottom:12px; }
.grid2, .grid3, .grid4 { display:grid; grid-template-columns:1fr; gap:12px; }
.grid2 > *, .grid3 > *, .grid4 > * { margin-bottom:0; min-width:0; }
@media (min-width:640px) { .grid4, .grid3 { grid-template-columns:1fr 1fr; } .grid2 { grid-template-columns:1fr 1fr; } }
@media (min-width:860px) { .grid2 { grid-template-columns:1.3fr 1fr; } .grid3 { grid-template-columns:repeat(3,1fr); }
  .grid4 { grid-template-columns:repeat(4,1fr); } }
.hero-num { font-size:40px; font-weight:700; letter-spacing:-0.03em; line-height:1.1; margin:6px 0; }
.tile { background:var(--card); border-radius:14px; padding:14px 16px; }
.tile-label { font-size:13px; color:var(--sub); }
.tile-value { font-size:26px; font-weight:600; font-variant-numeric:tabular-nums; }
.org-name { font-weight:700; display:flex; align-items:center; gap:8px; }
.org-role { margin:4px 0 8px; font-size:15px; }
.kv { display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:14px; padding:3px 0; color:var(--sub); }
.kv strong { color:var(--ink); }
.lkey { display:inline-block; width:14px; height:3px; border-radius:2px; background:var(--c); vertical-align:middle; margin-right:6px; flex-shrink:0; }
@media (prefers-color-scheme: dark) { .lkey { background:var(--cd); } }
.pill { display:inline-block; font-size:12px; font-weight:600; padding:2px 9px; border-radius:99px; white-space:nowrap; }
.p0 { background:var(--p0); color:var(--p0t); } .p1 { background:var(--p1); color:var(--p1t); }
.p2 { background:var(--p2); color:var(--p2t); } .p3 { background:var(--p3); color:var(--p3t); }
.p4 { background:var(--p4); color:var(--p4t); } .pn { background:var(--rule); color:var(--sub); }
.list { background:var(--card); border-radius:14px; overflow:hidden; margin-bottom:12px; }
.row { display:flex; gap:12px; padding:13px 16px; border-bottom:1px solid var(--rule); scroll-margin-top:80px; }
.row:last-child { border-bottom:none; } .row.hl { background:var(--hl); box-shadow:inset 3px 0 0 var(--accent); }
.row-main { flex:1; min-width:0; } .row-title { font-weight:600; }
.row-sub { color:var(--sub); font-size:14px; display:block; font-weight:400; }
.check { width:20px; height:20px; border-radius:50%; border:2px solid var(--rule); flex-shrink:0; margin-top:2px; }
.check.doing { border-color:var(--accent); } .check.done { background:var(--up); border-color:var(--up); }
.up { color:var(--up); font-weight:600; } .down { color:var(--down); font-weight:600; }
.chip { display:inline-block; font-size:12px; padding:1px 7px; border-radius:6px; background:var(--rule); color:var(--ink);
  white-space:nowrap; margin:2px 4px 2px 0; text-decoration:none; font-variant-numeric:tabular-nums; }
a.chip { color:var(--accent); }
.st { display:inline-flex; align-items:center; gap:4px; font-size:12px; font-weight:600; padding:1px 8px; border-radius:99px;
  background:var(--rule); color:var(--ink); white-space:nowrap; }
.st-doing { background:transparent; box-shadow:inset 0 0 0 1.5px var(--accent); color:var(--accent); }
.st-done { background:var(--up); color:#fff; } .st-dropped { color:var(--sub); text-decoration:line-through; }
.flag { display:flex; gap:8px; align-items:flex-start; background:var(--warn-bg); color:var(--warn-ink); border-radius:10px;
  padding:8px 10px; font-size:13px; margin-top:8px; }
.flag svg { flex-shrink:0; margin-top:2px; }
.tag { font-size:12px; padding:1px 7px; border-radius:6px; background:var(--rule); white-space:nowrap; }
.t-verified { background:#d8f3dc; color:#1b5e20; } .t-corroborated { background:#dcebfb; color:#0d366b; }
.t-contradicted, .t-overstated { background:#fde2e1; color:#8a1c14; } .t-unverified, .t-unsupported { background:#fff1cc; color:#6b4a00; }
@media (prefers-color-scheme: dark) { .t-verified { background:#1e3a24; color:#9be7a5; } .t-corroborated { background:#102a4a; color:#9ec5f4; }
  .t-contradicted, .t-overstated { background:#3d1714; color:#ffb4ab; } .t-unverified, .t-unsupported { background:#3a2e0b; color:#ffd60a; } }
.chart-title { font-weight:600; margin-bottom:6px; }
.legend { display:flex; gap:14px; flex-wrap:wrap; font-size:13px; color:var(--sub); margin-bottom:6px; }
.legend span { display:inline-flex; align-items:center; }
.plot { position:relative; min-height:120px; outline:none; border-radius:8px; }
.plot:focus-visible { box-shadow:0 0 0 2px var(--accent); }
.plot svg { display:block; overflow:visible; }
.plot .grid { stroke:var(--grid); stroke-width:1; } .plot .axis { fill:var(--sub); font-size:11px; }
.plot .dlabel { fill:var(--ink); font-size:12px; font-weight:600; }
.plot .cross { stroke:var(--sub); stroke-width:1; } .plot .hit { fill:transparent; cursor:crosshair; }
.noscript-note { font-size:13px; color:var(--sub); }
.js .noscript-note { display:none; }
.tip { position:fixed; pointer-events:none; background:var(--card); color:var(--ink); border:1px solid var(--rule);
  border-radius:8px; padding:8px 10px; font-size:13px; box-shadow:0 4px 16px rgba(0,0,0,.15); z-index:50; display:none;
  min-width:120px; max-width:280px; }
.tip .tv { font-weight:700; font-variant-numeric:tabular-nums; } .tip .tn { color:var(--sub); }
.bars { display:flex; flex-direction:column; gap:8px; }
.brow { display:grid; grid-template-columns:minmax(96px,40%) 1fr; gap:10px; align-items:center; outline:none; border-radius:6px; }
.brow:hover .bfill, .brow:focus .bfill { filter:brightness(1.12); }
.brow:focus-visible { box-shadow:0 0 0 2px var(--accent); }
.blabel { font-size:14px; line-height:1.3; } .btrack { display:flex; align-items:center; gap:8px; min-width:0; }
.bfill { height:14px; background:var(--s1); border-radius:0 4px 4px 0; flex-shrink:0; }
.bval { font-size:13px; font-weight:600; white-space:nowrap; font-variant-numeric:tabular-nums; }
.tableview { margin-top:10px; font-size:13px; } .tableview summary { color:var(--accent); cursor:pointer; }
.tablewrap { overflow-x:auto; }
table { border-collapse:collapse; width:100%; }
td, th { text-align:left; padding:6px 6px; border-top:1px solid var(--rule); vertical-align:top; }
th { font-weight:600; color:var(--sub); font-size:13px; }
td.num, th.num { white-space:nowrap; font-variant-numeric:tabular-nums; }
table.dims { font-size:14px; margin-top:8px; }
@media (max-width:520px) {
  table.stack tr.head { display:none; }
  table.stack, table.stack tbody, table.stack tr, table.stack td { display:block; width:auto; }
  table.stack tr { border-top:1px solid var(--rule); padding:8px 0; }
  table.stack td { border-top:none; padding:1px 0; }
  table.stack td.num { display:inline-block; font-weight:600; }
  table.stack td.lead { display:inline-block; font-weight:600; margin-right:8px; }
  table.stack td.lead-tag { display:inline-block; margin-left:8px; }
}
.toolbar { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:12px; font-size:14px; }
.toolbar input[type=search], .toolbar select { font:inherit; font-size:15px; padding:6px 10px; border-radius:9px;
  border:1px solid var(--rule); background:var(--card); color:var(--ink); min-width:0; }
.toolbar input[type=search] { flex:1 1 180px; }
.toolbar label { display:inline-flex; align-items:center; gap:6px; }
.rrow { border-bottom:1px solid var(--rule); padding:0 16px; } .rrow:last-child { border-bottom:none; }
.rrow summary { display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center; padding:12px 0; cursor:pointer; list-style:none; }
.rrow summary::-webkit-details-marker { display:none; }
.rrow summary::after { content:"\203A"; color:var(--sub); font-size:20px; line-height:1; transition:transform .15s; }
.rrow[open] summary::after { transform:rotate(90deg); }
.rtitle { flex:1 1 180px; min-width:0; font-weight:600; }
.rscore { font-weight:700; font-variant-numeric:tabular-nums; min-width:2ch; text-align:right; }
.rbody { padding:0 0 14px; }
.kitem { padding:8px 0; border-top:1px solid var(--rule); }
.swot { display:grid; grid-template-columns:1fr; gap:12px; }
@media (min-width:640px) { .swot { grid-template-columns:1fr 1fr; } }
.quad { background:var(--card); border-radius:14px; padding:14px 16px; min-width:0; }
.quad-head { display:flex; align-items:center; gap:8px; margin-bottom:4px; }
.quad-head strong { font-size:16px; } .quad-kind { font-size:12px; color:var(--sub); margin-left:auto; }
.qitem { padding:9px 0; border-top:1px solid var(--rule); } .qitem:first-of-type { border-top:none; }
.qid { font-weight:700; color:var(--sub); font-size:12px; margin-right:6px; font-variant-numeric:tabular-nums; }
.scope { display:flex; flex-wrap:wrap; gap:6px; margin:4px 0 12px; }
.scope button { font:inherit; font-size:14px; padding:5px 12px; border-radius:99px; border:1px solid var(--rule);
  background:var(--card); color:var(--ink); cursor:pointer; }
.scope button.on { background:var(--accent); border-color:var(--accent); color:#fff; }
.js .swot-scope { display:none; } .js .swot-scope.on { display:block; }
.strategy { padding:12px 0; border-top:1px solid var(--rule); } .strategy:first-of-type { border-top:none; }
.links a { margin-right:10px; }
details.card summary { cursor:pointer; font-weight:600; }
a { color:var(--accent); } ul { padding-left:20px; } li { margin:5px 0; }
.foot { margin-top:36px; font-size:13px; color:var(--sub); }
"""

JS = r"""
(function () {
  "use strict";
  var doc = document.documentElement;
  var VIEWS = ["overview", "trends", "roles", "swot", "plan", "evidence"];
  var tip = document.getElementById("tip");
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function isDark() { return !!(mq && mq.matches); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) {
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }

  /* ---------- views ---------- */
  function show() {
    var h = decodeURIComponent((location.hash || "#overview").slice(1));
    var parts = h.split("/"), v = parts[0];
    if (VIEWS.indexOf(v) < 0) v = "overview";
    VIEWS.forEach(function (n) { document.getElementById("v-" + n).classList.toggle("on", n === v); });
    document.querySelectorAll(".seg a").forEach(function (a) {
      a.classList.toggle("on", a.getAttribute("href") === "#" + v); });
    renderAll();
    document.querySelectorAll(".row.hl").forEach(function (r) { r.classList.remove("hl"); });
    if (parts[1]) {
      var el = document.getElementById("act-" + parts[1]);
      if (el) { el.classList.add("hl"); el.scrollIntoView({block: "center"}); }
    } else { window.scrollTo(0, 0); }
  }

  /* ---------- tooltip ---------- */
  function place(x, y) {
    var px = x + 14, py = y + 14;
    if (px + tip.offsetWidth > innerWidth - 8) px = Math.max(8, x - tip.offsetWidth - 14);
    if (py + tip.offsetHeight > innerHeight - 8) py = Math.max(8, y - tip.offsetHeight - 14);
    tip.style.left = px + "px"; tip.style.top = py + "px";
  }
  function hideTip() { tip.style.display = "none"; }

  /* ---------- line charts, drawn at the real container width ---------- */
  function fmtDate(iso) {
    var m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    var p = iso.split("-"); return (+p[2]) + " " + m[(+p[1]) - 1];
  }
  function renderLine(el) {
    var d = el._d; if (!d) return;
    var W = el.clientWidth; if (!W) return;
    var dark = isDark(), narrow = W < 440, multi = d.series.length > 1;
    var H = d.compact ? 120 : (narrow ? 190 : 230);
    var pl = 34, pr = (multi && !narrow && !d.compact) ? 112 : 18, pt = 12, pb = 26;
    var iw = Math.max(40, W - pl - pr), ih = H - pt - pb, n = d.dates.length, ymax = d.ymax || 1;
    function x(i) { return pl + (n === 1 ? iw / 2 : i * iw / (n - 1)); }
    function y(v) { return pt + ih - (v / ymax) * ih; }
    var s = '<svg width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(d.title) + '">';
    d.ticks.forEach(function (t) {
      s += '<line class="grid" x1="' + pl + '" x2="' + (pl + iw) + '" y1="' + y(t) + '" y2="' + y(t) + '"/>';
      s += '<text class="axis" x="' + (pl - 8) + '" y="' + (y(t) + 4) + '" text-anchor="end">' + t + '</text>';
    });
    var maxLabels = Math.max(2, Math.floor(iw / 64)), step = Math.max(1, Math.ceil(n / maxLabels));
    for (var i = 0; i < n; i++) {
      if (i % step === 0 || i === n - 1) {
        if (i !== n - 1 && n - 1 - i < step && i !== 0) continue;
        s += '<text class="axis" x="' + x(i) + '" y="' + (H - 8) + '" text-anchor="' +
          (n === 1 ? "middle" : i === 0 ? "start" : i === n - 1 ? "end" : "middle") + '">' + fmtDate(d.dates[i]) + '</text>';
      }
    }
    var labels = [];
    d.series.forEach(function (ser) {
      var col = dark ? ser.cd : ser.c, pts = [];
      ser.values.forEach(function (v, i) { if (v !== null && v !== undefined) pts.push([x(i), y(v), v]); });
      if (!pts.length) return;
      if (pts.length > 1) s += '<path d="M' + pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" L") +
        '" fill="none" stroke="' + col + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
      var surface = dark ? "#1c1c1e" : "#ffffff";
      pts.forEach(function (p) { s += '<circle cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="4" fill="' + col +
        '" stroke="' + surface + '" stroke-width="2"/>'; });
      var last = pts[pts.length - 1];
      labels.push({y: last[1], x: last[0], text: ser.name + " " + Math.round(last[2])});
    });
    if (pr > 18) {
      labels.sort(function (a, b) { return a.y - b.y; });
      for (var k = 1; k < labels.length; k++) if (labels[k].y - labels[k - 1].y < 14) labels[k].y = labels[k - 1].y + 14;
      labels.forEach(function (l) { s += '<text class="dlabel" x="' + (l.x + 9) + '" y="' + (l.y + 4) + '">' + esc(l.text) + '</text>'; });
    }
    s += '<line class="cross" x1="0" x2="0" y1="' + pt + '" y2="' + (pt + ih) + '" visibility="hidden"/>';
    s += '<rect class="hit" x="' + pl + '" y="' + pt + '" width="' + iw + '" height="' + ih + '"/></svg>';
    el.innerHTML = s;
    var svg = el.querySelector("svg"), cross = el.querySelector(".cross");
    function idxAt(clientX) {
      var r = svg.getBoundingClientRect(), sx = clientX - r.left;
      if (n === 1) return 0;
      return Math.max(0, Math.min(n - 1, Math.round((sx - pl) / (iw / (n - 1)))));
    }
    function showAt(i, cx, cy) {
      el._i = i;
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
      tip.textContent = "";
      var head = document.createElement("div"); head.className = "tn"; head.textContent = fmtDate(d.dates[i]); tip.appendChild(head);
      d.series.forEach(function (ser) {
        var v = ser.values[i]; if (v === null || v === undefined) return;
        var row = document.createElement("div"), key = document.createElement("i");
        key.className = "lkey"; key.style.background = isDark() ? ser.cd : ser.c; row.appendChild(key);
        var val = document.createElement("span"); val.className = "tv"; val.textContent = (Math.round(v * 10) / 10) + d.unit + " ";
        var nm = document.createElement("span"); nm.className = "tn"; nm.textContent = ser.name;
        row.appendChild(val); row.appendChild(nm); tip.appendChild(row);
      });
      tip.style.display = "block"; place(cx, cy);
    }
    svg.addEventListener("pointermove", function (e) { showAt(idxAt(e.clientX), e.clientX, e.clientY); });
    svg.addEventListener("pointerleave", function () { hideTip(); cross.setAttribute("visibility", "hidden"); });
    el.onkeydown = function (e) {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      var i = el._i === undefined ? n - 1 : el._i + (e.key === "ArrowRight" ? 1 : -1);
      i = Math.max(0, Math.min(n - 1, i));
      var r = svg.getBoundingClientRect(); showAt(i, r.left + x(i), r.top + pt);
    };
    el.onblur = function () { hideTip(); cross.setAttribute("visibility", "hidden"); };
  }
  function renderAll() {
    document.querySelectorAll(".plot").forEach(function (el) {
      if (!el._d) { var src = document.getElementById(el.getAttribute("data-src")); if (src) el._d = JSON.parse(src.textContent); }
      if (el.offsetParent !== null) renderLine(el);
    });
  }
  var rt; window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(renderAll, 120); });
  if (mq && mq.addEventListener) mq.addEventListener("change", renderAll);

  /* ---------- bar tooltips ---------- */
  document.querySelectorAll(".brow").forEach(function (b) {
    function on(e) {
      tip.textContent = b.getAttribute("data-tip"); tip.style.display = "block";
      if (e.clientX) place(e.clientX, e.clientY);
      else { var r = b.getBoundingClientRect(); place(r.left, r.bottom); }
    }
    b.addEventListener("pointermove", on); b.addEventListener("focus", on);
    b.addEventListener("pointerleave", hideTip); b.addEventListener("blur", hideTip);
  });

  /* ---------- role filters ---------- */
  var fq = document.getElementById("f-q"), fo = document.getElementById("f-org"), ff = document.getElementById("f-fam"),
      fb = document.getElementById("f-blocked"), fc = document.getElementById("f-count");
  function filt() {
    var q = (fq.value || "").toLowerCase(), shown = 0;
    document.querySelectorAll("#roles .rrow").forEach(function (r) {
      var ok = (!fo.value || r.dataset.org === fo.value) && (!ff.value || r.dataset.family === ff.value) &&
        (!fb.checked || r.dataset.blocked !== "1") && (!q || r.dataset.text.indexOf(q) >= 0);
      r.style.display = ok ? "" : "none"; if (ok) shown++;
    });
    fc.textContent = shown + (shown === 1 ? " role" : " roles");
  }
  if (fo) { [fq, fo, ff, fb].forEach(function (c) { c.addEventListener("input", filt); c.addEventListener("change", filt); }); filt(); }

  /* ---------- SWOT scope ---------- */
  document.querySelectorAll(".scope button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var s = btn.getAttribute("data-scope");
      document.querySelectorAll(".scope button").forEach(function (b) {
        var on = b === btn; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on ? "true" : "false"); });
      document.querySelectorAll(".swot-scope").forEach(function (p) { p.classList.toggle("on", p.id === "scope-" + s); });
    });
  });

  window.addEventListener("hashchange", show);
  show();
})();
"""
