"""The page script's level maths (JS_LEVELS) agrees with _levels.py: the next level, the quests and the panel text.

Runs the page's own maths and rendering functions in Node.js (a JavaScript runtime) on the same page data
the Python side uses, for every journey (best overall and each organisation). Skipped when Node.js is not
installed. No network: the script reads nothing but the data it is given.
"""
import json
import os
import shutil
import subprocess
import unittest
from unittest import mock

import helpers as H
import _dashboard_assets as A
import _levels as L
import _levels_html as LH
import build_dashboard as B
import test_levels as TL

NODE = shutil.which("node")


def page_script():
    """The parts of the page script the level view needs, without the page itself (no document, no storage)."""
    core = A.JS_CORE
    head = core[core.index("const W = D.weights"):core.index("// Mark an element as entering")]
    maths = core[core.index("// ---------- scoring and projection"):core.index("// ---------- helpers ----------")]
    return "globalThis.matchMedia = () => ({matches: false});\n" + head + maths + A.JS_LEVELS


DRIVER = r"""
const dateOK = fmtDate("2026-11-12") === "12 Nov 2026";      // needs full date formatting for Australian English
const out = {dateOK, journeys: {}};
["best"].concat(D.orgOrder).forEach(org => {
  state.org = org;
  const rs = journeyRoles(), nl = nextLevel(rs), qs = questsFor(rs, nl);
  const set = s => !s ? null : {ids: s.ids, date: s.date, fit: s.fit, exact: s.exact, role: s.role.id,
                         chance: s.chance == null ? null : Math.round(s.chance * 1e9) / 1e9};
  out.journeys[org] = {
    nl: {lead: nl.r.id, level: nl.level, top: nl.top, target: nl.target || null, toNext: nl.top ? null : nl.toNext,
         plan: nl.plan ? [nl.plan.exp, nl.plan.best, nl.plan.date] : null, reachable: nl.top ? null : nl.reachable,
         set: set(nl.set), bestCase: nl.top || nl.reachable ? null : set(nl.bestCase),
         missing: nl.missing ? {points: nl.missing.points, ceiling: nl.missing.ceiling, role: nl.missing.r.id,
                                room: nl.missing.room.map(x => [x.dim, x.points, x.covered])} : null},
    quests: qs.map(q => [q.a.id, q.exp, q.works, Math.round(q.rate * 1e6) / 1e6, q.r.id, q.fitAfter, q.leadExp, q.leadWorks, q.crit, q.bc]),
    verdict: verdictHTML(nl), via: qs.map(q => viaLine(q, nl))};
});
console.log(JSON.stringify(out));
"""


def run_page(page):
    prog = "const D = %s;\n%s\n%s" % (json.dumps(page), page_script(), DRIVER)
    res = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=120)
    if res.returncode:
        raise AssertionError("the page script failed in Node.js:\n" + res.stderr[-2000:])
    return json.loads(res.stdout)


def py_story(page):
    """The same summary as DRIVER, from _levels.py and _levels_html.py."""
    out = {}
    for org in ["best"] + page["orgOrder"]:
        if org == "best":
            rs = L.journey_roles(page["roles"])
        else:
            lead = next(r for r in page["roles"] if r["id"] == page["orgs"][org]["best"])
            rs = L.journey_roles(page["roles"], lead, org)
        nl = L.next_level(rs, page["actions"], page["caps"], page["weights"], page["meta"]["run_date"])
        qs = L.quests(rs, page["actions"], page["caps"], page["weights"], nl)

        def found(s):
            return s and {"ids": s["ids"], "date": s["date"], "fit": s["fit"], "exact": s["exact"], "role": s["role"]["id"],
                          "chance": None if s.get("chance") is None else round(s["chance"] * 1e9) / 1e9}
        m = nl.get("missing")
        out[org] = {
            "nl": {"lead": rs[0]["id"], "level": nl["level"], "top": nl["top"], "target": nl.get("target"),
                   "toNext": nl.get("points_to_next"),
                   "plan": [nl["plan"]["fit_expected"], nl["plan"]["fit_best"], nl["plan"]["date"]] if "plan" in nl else None,
                   "reachable": nl.get("reachable"), "set": found(nl.get("set")),
                   "bestCase": None if nl["top"] or nl["reachable"] else found(nl.get("best_case")),
                   "missing": m and {"points": m["points"], "ceiling": m["ceiling"], "role": m["role"]["id"],
                                     "room": [[x["dimension"], x["points"], x["covered"]] for x in m["room"]]}},
            "quests": [[q["a"]["id"], q["exp"], q["works"], round(q["rate"] * 1e6) / 1e6, q["role"]["id"], q["fit_after"],
                        q["lead_exp"], q["lead_works"], q["crit"], q["bc"]] for q in qs],
            "verdict": LH.verdict(page, nl, rs[0]), "via": [LH.via(q, rs[0]) for q in qs]}
    return out


@unittest.skipUnless(NODE, "Node.js is not installed")
class PageAgreesWithPython(unittest.TestCase):
    maxDiff = None
    def check(self, page):
        js, py = run_page(page), py_story(page)
        self.assertEqual(set(js["journeys"]), set(py))
        for org, want in py.items():
            got = json.loads(json.dumps(js["journeys"][org]))
            self.assertEqual(got["nl"], json.loads(json.dumps(want["nl"])), org)
            self.assertEqual(got["quests"], json.loads(json.dumps(want["quests"])), org)
            if js["dateOK"]:                                           # same words, once the markup is set aside
                self.assertEqual(TL.plain(got["verdict"]), TL.plain(want["verdict"]), org)
                self.assertEqual([TL.plain(v) for v in got["via"]], [TL.plain(v) for v in want["via"]], org)
        return js, py

    def test_lifted_role_fixture(self):
        js, _ = self.check(TL.lifted_fixture())
        best = js["journeys"]["best"]
        self.assertEqual((best["nl"]["set"]["ids"], best["nl"]["set"]["role"]), (["A01"], "globex:7"))
        self.assertEqual(best["quests"][0][:3], ["A01", 5.2, 6])
        if js["dateOK"]:
            self.assertIn("by lifting your fit for Solutions Lead (Globex Labs) from 37 to 44.2", TL.plain(best["verdict"]))

    def test_demo_every_journey(self):
        ws = H.copy_demo(self)
        with mock.patch("sys.stdout"):
            self.assertEqual(B.main(["--workspace", ws]), 0)
        with open(os.path.join(ws, "report", "index.html"), encoding="utf-8") as fh:
            page = json.loads(fh.read().split('<script type="application/json" id="data">')[1].split("</script>")[0])
        self.check(page)


if __name__ == "__main__":
    unittest.main()
