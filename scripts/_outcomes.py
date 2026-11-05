"""The outcome opt-in: a numbers-only export the person can choose to share, and the plain consent screen for it.

What is in it: for each application sent, the fit and the seven factor scores LVLme gave the role on the day, the
bands, the rubric version, the role family and what happened (interview yes, no or still waiting; offer likewise).
What is never in it: your CV, evidence, names of people, organisations, roles, links, dates down to the day, or any
text you wrote. Nothing is sent anywhere by LVLme: the export is a file on your computer and the page only offers to
save it. If you choose to share it, you send it yourself. No network calls here.
"""
import glob
import html
import json

import _calibration as CAL
import _common as C

SCHEMA = "lvlme-outcomes-1"
IN = ["For each application you sent: the fit score and the seven factor scores (0 to 5) LVLme gave that role on the day.",
      "The chance bands (for example Low or Moderate) and the version of the scoring rules.",
      "The role family (for example product or customer success) and the month you applied.",
      "What happened: interview yes, no or still waiting; offer yes, no or still waiting."]
NOT_IN = ["Your CV, your evidence, your notes or anything you wrote.",
          "Names of people, organisations or roles, and links.",
          "Your name, email, location or the exact dates.",
          "Anything about the roles you did not apply to."]
CONSENT = ("Sharing these numbers is your choice. LVLme sends nothing anywhere: this is a file on your computer. "
           "If you share it, you send it yourself, and you can delete it at any time.")


def rows_of(ws, today):
    doc = C.load_json(C.wpath(ws, "campaign", "applications.json"), None)
    runs = CAL.load_runs(ws)
    scored = dict(runs)
    meta = {}
    for f in glob.glob(C.wpath(ws, "eval", "runs", "*.json")):
        run = C.load_json(f, {}) or {}
        meta[run.get("run_date")] = run.get("rubric_version")
    rows, _ = CAL.results(ws, doc, today, runs)
    by_id = {a["id"]: a for a in (doc or {}).get("applications") or []}
    out = []
    for r in rows:
        app = by_id[r["id"]]
        run_date = r["pred"]["run_date"]
        role = (scored.get(run_date) or {}).get(app.get("role_id")) or {}
        scores = role.get("scores") or {}
        out.append({"rubric_version": meta.get(run_date), "family": role.get("family") or "unknown",
                    "month": (app.get("applied_on") or "")[:7], "fit": r["pred"].get("fit"),
                    "factor_scores": {d: scores[d]["score"] for d in C.DIMENSIONS if d in scores},
                    "interview_band": r["pred"].get("interview_band"), "offer_band": r["pred"].get("offer_band"),
                    "warm_path": bool(r["pred"].get("warm")), "interview": r["out"]["interview"], "offer": r["out"]["offer"]})
    return out


def build(ws, today):
    rows = rows_of(ws, today)
    return {"schema": SCHEMA, "applications": len(rows), "rows": rows,
            "note": "Numbers only. No CV, names, organisations, roles, links or exact dates."}


def page(export):
    """The consent screen: what is in, what is not, the exact file, and a save button behind a tick box."""
    blob = json.dumps(export, indent=2)
    li = lambda xs: "".join("<li>%s</li>" % html.escape(x) for x in xs)  # noqa: E731
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Share my numbers</title><style>
:root{color-scheme:light dark;--bg:#f2f2f5;--card:#fff;--ink:#1d1d1f;--sub:#56565b;--rule:#d8d8de;--lv:#FF4A1C;--lvi:#0C0E12}
@media (prefers-color-scheme:dark){:root{--bg:#111113;--card:#1c1c1e;--ink:#f5f5f7;--sub:#b8b8be;--rule:#38383c}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"SF Pro Text",Helvetica,Arial,sans-serif}
main{max-width:600px;margin:0 auto;padding:24px 20px 56px}h1{font-size:28px;letter-spacing:-.02em;margin:8px 0}
.c{background:var(--card);border-radius:18px;padding:18px 20px;margin:14px 0}h2{font-size:13px;text-transform:uppercase;letter-spacing:.02em;color:var(--sub);margin:0 0 6px}
ul{margin:6px 0 0;padding-left:20px;color:var(--sub)}label{display:flex;gap:10px;align-items:flex-start;margin:12px 0;min-height:44px}
input{width:22px;height:22px;margin-top:2px;accent-color:var(--lv)}button{min-height:44px;padding:0 22px;border-radius:999px;border:0;background:var(--lv);color:var(--lvi);font:inherit;font-weight:600;cursor:pointer}
button:disabled{opacity:.4;cursor:not-allowed}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:240px;overflow:auto;background:var(--bg);border-radius:12px;padding:12px}
a{color:var(--ink)}</style></head><body><main>
<p><a href="index.html">Back to Today</a></p><h1>Share my numbers</h1><p style="color:var(--sub)">%s</p>
<div class="c"><h2>What is in it</h2><ul>%s</ul></div><div class="c"><h2>What is never in it</h2><ul>%s</ul></div>
<div class="c"><h2>The exact file (%d %s)</h2><pre id="j">%s</pre>
<label><input type="checkbox" id="ok"><span>I have read this and I choose to save these numbers as a file I can share.</span></label>
<button id="go" disabled>Save the file</button><p style="color:var(--sub);font-size:14px">Nothing is sent. The file is saved on this computer.</p></div>
</main><script>var ok=document.getElementById("ok"),go=document.getElementById("go");ok.addEventListener("change",function(){go.disabled=!ok.checked});
go.addEventListener("click",function(){var b=new Blob([document.getElementById("j").textContent],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="lvlme-outcomes.json";a.click()});</script></body></html>
""" % (html.escape(CONSENT), li(IN), li(NOT_IN), export["applications"], "application" if export["applications"] == 1 else "applications",
       html.escape(blob))
