"""build_dashboard.py: projection rules, colour slots, optional views, the history, copy rules, one yardstick."""
import html
import json
import os
import re
import shutil
import subprocess
import unittest
from unittest import mock

import helpers as H
import _dashboard_assets as A
import build_dashboard as B

WEIGHTS = [25, 20, 20, 10, 10, 10, 5]
CAPS = [0, 1, 2, 1, 1, 1, 3]


def role(s, org="acme", family="tpm", lc="australia_nz", rid="acme:1", hard=False):
    return {"id": rid, "org": org, "family": family, "lc": lc, "s": list(s), "hard": hard,
            "fit": B.fit_of(s, WEIGHTS)}


def action(aid, effects, p=0.5, status="todo"):
    return {"id": aid, "status": status, "p": p, "effects": effects}


def page_data(ws):
    with open(os.path.join(ws, "report", "index.html"), encoding="utf-8") as fh:
        page = fh.read()
    blob = re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1)
    return page, json.loads(blob)


class ProjectionTests(unittest.TestCase):
    def test_expected_weights_by_chance_and_best_case_lands(self):
        r = role([2, 2, 1, 2, 2, 5, 1])
        acts = [action("A01", [{"dimension": "D3", "set_at_least": 3, "scope": {}}], p=0.5)]
        exp, s = B.project(r, acts, CAPS, WEIGHTS, "exp")
        self.assertAlmostEqual(s[2], 2.0)              # 1 + 0.5 x (3 - 1)
        best, s = B.project(r, acts, CAPS, WEIGHTS, "best")
        self.assertEqual(s[2], 3)
        self.assertEqual(best, round(r["fit"] + 2 / 5.0 * 20, 1))
        self.assertLess(exp, best)

    def test_caps_and_five_limit(self):
        r = role([3, 2, 4, 2, 2, 5, 1])
        acts = [action("A01", [{"dimension": "D3", "delta": 5, "scope": {}}, {"dimension": "D1", "delta": 2, "scope": {}},
                               {"dimension": "D7", "delta": 4, "scope": {}}], p=1)]
        _, s = B.project(r, acts, CAPS, WEIGHTS, "best")
        self.assertEqual(s[2], 5)   # cap 2 over 4 would be 6, but never above 5
        self.assertEqual(s[0], 3)   # D1 cap 0: years in the role don't change
        self.assertEqual(s[6], 4)   # D7 cap 3 over 1

    def test_scope_and_done_actions(self):
        r = role([2, 2, 1, 2, 2, 5, 1], org="globex", family="product")
        acts = [action("A01", [{"dimension": "D2", "delta": 1, "scope": {"orgs": ["acme"]}}], p=1),
                action("A02", [{"dimension": "D2", "delta": 1, "scope": {"families": ["tpm"]}}], p=1),
                action("A03", [{"dimension": "D4", "delta": 1, "scope": {}}], p=1, status="done"),
                action("A04", [{"dimension": "D5", "delta": 1, "scope": {"location_classes": ["australia_nz"]}}], p=1)]
        _, s = B.project(r, acts, CAPS, WEIGHTS, "best")
        self.assertEqual(s, [2, 2, 1, 2, 3, 5, 1])   # only A04 applies: out of scope, or already in today's scores

    def test_hard_eligibility_block_keeps_d6_at_zero(self):
        acts = [action("A01", [{"dimension": "D6", "set_at_least": 4, "scope": {}}], p=1)]
        _, s = B.project(role([1, 1, 1, 0, 2, 0, 1], hard=True), acts, CAPS, WEIGHTS, "best")
        self.assertEqual(s[5], 0)
        _, s = B.project(role([1, 1, 1, 0, 2, 0, 1]), acts, CAPS, WEIGHTS, "best")
        self.assertEqual(s[5], 1)   # a blocker the plan can clear, within the D6 cap

    def test_parked_actions_are_left_out(self):
        r = role([2, 2, 1, 2, 2, 5, 1])
        acts = [action("A01", [{"dimension": "D3", "set_at_least": 3, "scope": {}}], p=1, status="later")]
        self.assertEqual(B.project(r, acts, CAPS, WEIGHTS, "best")[1], r["s"])   # off until switched on in the page

    def test_effects_estimated_from_expected_points(self):
        weights = dict(zip(B.DIMS, WEIGHTS))
        effects, derived = B.action_effects({"dimension": "D3", "expected_points": 8, "orgs": ["acme"]}, weights)
        self.assertTrue(derived)
        self.assertEqual(effects, [{"dimension": "D3", "delta": 2.0, "scope": {"orgs": ["acme"]}}])
        effects, derived = B.action_effects({"dimension": "D3", "expected_points": 8, "effects": []}, weights)
        self.assertEqual((effects, derived), ([], False))   # an explicit empty list means no score change


class SlotTests(unittest.TestCase):
    def test_up_to_eight_orgs_get_their_own_colour(self):
        ids = ["o%d" % i for i in range(8)]
        groups, group_of = B.org_groups(ids, {})
        self.assertEqual(list(groups), ids)
        self.assertEqual(groups["o0"]["c"], "#2a78d6")
        self.assertEqual(len({g["c"] for g in groups.values()}), 8)

    def test_more_than_eight_fold_into_other(self):
        ids = ["o%d" % i for i in range(11)]
        groups, group_of = B.org_groups(ids, {"o0": "Zero"})
        self.assertEqual(len(groups), 8)
        self.assertEqual(groups["o0"]["name"], "Zero")
        self.assertEqual(groups[B.OTHER_KEY]["members"], ["o7", "o8", "o9", "o10"])
        self.assertEqual(group_of["o9"], B.OTHER_KEY)


class CopyTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(B.clean("Fix it — now, 2–3 weeks - then **ship**"), "Fix it, now, 2 to 3 weeks, then ship")
        self.assertEqual(B.clean("the D4 edge most lack"), "the Org-specific edge most lack")
        self.assertEqual(B.clean("raises D3 to 3"), "raises Warm path to 3")
        self.assertEqual(B.clean("forward-deployed"), "forward-deployed")


class DemoPageTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def build(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(B.main(["--workspace", self.ws]), 0)
        return page_data(self.ws)

    def test_unjudged_run_is_never_day_one(self):
        """A run saved with nothing judged (before score.py refused them) is skipped, not used as Day 1."""
        fake = H.load(os.path.join(self.ws, "eval", "runs", "2026-10-04.json"))
        fake.update(run_date="2026-09-27", counts=dict(fake["counts"], judged=0, not_judged=fake["counts"]["roles"]))
        H.save(os.path.join(self.ws, "eval", "runs", "2026-09-27.json"), fake)
        with mock.patch("sys.stderr") as err:
            page, d = self.build()
        self.assertEqual(d["runs"][0]["date"], "2026-10-04")
        self.assertEqual(d["meta"]["baseline"], "2026-10-04")
        self.assertIn("ignoring eval/runs/2026-09-27.json", "".join(c.args[0] for c in err.write.call_args_list))

    def test_page_data(self):
        page, d = self.build()
        acts = {a["id"]: a for a in d["actions"]}
        self.assertEqual(acts["A10"]["stale"], 4)                 # no movement since 2026-10-11
        self.assertEqual(acts["A04"]["effects"], [])
        self.assertTrue(acts["A08"]["derived"])
        self.assertEqual(acts["A01"]["group"], "done")
        roles = {r["id"]: r for r in d["roles"]}
        self.assertTrue(roles["acme:4100006"]["hard"])
        self.assertEqual(d["orgOrder"], ["acme", "globex", "initech"])
        self.assertEqual(d["orgs"]["initech"]["best"], "initech:i-0001")
        self.assertEqual([r["date"] for r in d["runs"]][0], "2026-10-04")
        self.assertEqual(d["meta"]["baseline"], "2026-10-04")
        self.assertFalse(d["meta"]["git"])                        # a plain folder: dates only
        self.assertTrue(all(r["commit"] is None for r in d["runs"]))
        self.assertEqual(d["ceil"]["target"], 85)
        self.assertEqual(d["swot"]["tows"][0]["a"], ["A05", "A06"])
        self.assertEqual(d["caps"], [0, 1, 3, 1, 1, 1, 2])
        self.assertNotIn("Jordan", page)                          # contact names, first names too, are hidden

    def test_optional_views_hide_without_their_files(self):
        os.remove(os.path.join(self.ws, "eval", "ceilings.json"))
        os.remove(os.path.join(self.ws, "eval", "swot.json"))
        _, d = self.build()
        self.assertIsNone(d["ceil"])
        self.assertIsNone(d["swot"])

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_record_uses_commits_in_a_git_workspace(self):
        git = ["git", "-C", self.ws, "-c", "user.name=Test", "-c", "user.email=test@example.com"]
        for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "runs"]):
            subprocess.run(git + cmd, check=True, capture_output=True)
        head = subprocess.run(git + ["log", "--format=%h", "-1"], capture_output=True, text=True).stdout.strip()
        _, d = self.build()
        self.assertTrue(d["meta"]["git"])
        self.assertEqual({r["commit"] for r in d["runs"]}, {head})

    def test_projection_in_agent_files(self):
        self.build()
        payload = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))
        top = payload["projection"]["roles"][0]
        self.assertEqual(top["role_id"], "initech:i-0001")
        self.assertLessEqual(top["fit_today"], top["fit_expected"])
        self.assertLessEqual(top["fit_expected"], top["fit_best_case"])
        self.assertEqual(payload["projection"]["end_date"], "2027-01-31")
        with open(os.path.join(self.ws, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as fh:
            self.assertIn("## Projection to 2027-01-31", fh.read())



class UnjudgedRoleTests(unittest.TestCase):
    """A role nobody has judged is "not judged yet": never a best role, a tile count, an unlock or a measured row."""

    def setUp(self):
        self.ws = H.copy_demo(self)
        path = os.path.join(self.ws, "eval", "runs", "2026-11-01.json")
        run = H.load(path)
        for r in run["roles"]:
            if r["org"] == "globex":
                r["judged"] = False
        run["per_org"]["globex"] = None
        H.save(path, run)
        with mock.patch("sys.stdout"):
            self.assertEqual(B.main(["--workspace", self.ws]), 0)
        self.page, self.d = page_data(self.ws)

    def read(self, name):
        with open(os.path.join(self.ws, "report", "for-agents", name), encoding="utf-8") as fh:
            return fh.read()

    def test_page_data_marks_them(self):
        d = self.d
        self.assertEqual(d["orgs"]["globex"]["judged"], 0)
        self.assertGreater(d["orgs"]["globex"]["count"], 0)
        judged = [r["judged"] for r in d["roles"]]
        self.assertEqual(judged, sorted(judged, reverse=True))          # judged roles first
        self.assertNotIn("globex", [g for g, v in d["runs"][-1]["orgs"].items() if v])
        for text in ("No role judged yet at", "of ${J.length} judged", "Not judged", "r.lc === m.home && r.judged",
                     "D.orgOrder.filter(g => D.orgs[g].judged)"):
            self.assertIn(text, self.page)

    def test_summary_and_agent_data_never_score_them(self):
        summary = self.read("SUMMARY.md")
        best = summary.split("## Best role at each organisation")[1].split("##")[0]
        self.assertIn("Globex Labs: no role judged yet (", best)
        top = summary.split("## Top 10 judged open roles")[1].split("##")[0]
        self.assertNotIn("Globex", top)
        self.assertNotIn("At Globex", summary)                          # no next level for a journey nobody measured
        payload = json.loads(self.read("dashboard.json"))
        self.assertIsNone(payload["per_org"]["globex"])
        self.assertTrue(all(not r["judged"] for r in payload["roles"] if r["org"] == "globex"))
        self.assertLess(payload["role_counts"]["judged"], payload["role_counts"]["open"])
        self.assertIn("No role judged yet (", self.page)                # the static summary too


class ParkedAndStaticTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def build(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(B.main(["--workspace", self.ws]), 0)
        return page_data(self.ws)

    def payload(self):
        return H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))

    def set_status(self, aid, status):
        plan = H.load(os.path.join(self.ws, "campaign", "plan.json"))
        next(a for a in plan["actions"] if a["id"] == aid)["status"] = status
        H.save(os.path.join(self.ws, "campaign", "plan.json"), plan)

    def test_parked_action_is_off_the_projection_and_the_next_level(self):
        self.set_status("A11", "dropped")
        self.build()
        dropped = self.payload()
        self.set_status("A11", "later")
        page, d = self.build()
        parked = self.payload()
        a11 = next(a for a in d["actions"] if a["id"] == "A11")
        self.assertEqual((a11["status"], a11["group"]), ("later", "later"))
        self.assertEqual(parked["projection"], dropped["projection"])          # no effect until switched on
        self.assertEqual(parked["levels"]["best_role"], dropped["levels"]["best_role"])
        self.assertNotIn("A11", [q["id"] for q in parked["levels"]["quests"]])
        self.assertNotIn("A11", [a["id"] for a in parked["actions_active"]])
        self.assertEqual(sorted(a["id"] for a in parked["actions_later"]), ["A11", "A12"])   # the demo parks A12 already
        with open(os.path.join(self.ws, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as fh:
            self.assertIn("## Parked for later", fh.read())
        script = page.split('<script type="application/json"')[1]
        self.assertIn('const switchable = a => live(a) || a.status === "later";', script)
        self.assertIn("const enabled = new Set(D.actions.filter(live)", script)   # parked starts switched off
        self.assertIn("if (!switchable(a)) return;", script)                     # but counts once switched on

    def test_static_summary_reads_without_javascript(self):
        page, d = self.build()
        body = page.split('<script type="application/json"')[0]
        section = re.search(r'<section class="card static-sum" id="staticSummary"[^>]*>(.*?)</section>', body, re.S).group(1)
        text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", section)))
        run = H.load(os.path.join(self.ws, "eval", "runs", "2026-11-01.json"))
        best = run["roles"][0]
        self.assertIn("Your numbers on 1 Nov 2026", text)
        self.assertIn("Best match %d of 100" % int(best["fit"] + 0.5), text)
        self.assertIn("Interview chance %s, offer chance %s" % (best["interview_band"], best["offer_band"]), text)
        self.assertIn("Level 3, Moderate", text)
        for org, b in run["per_org"].items():
            title = next(r["title"] for r in d["roles"] if r["id"] == b["role_id"])
            self.assertIn("%s %s %d %s %s" % (d["orgNames"][org], title, int(b["fit"] + 0.5), b["interview_band"],
                                              b["offer_band"]), text)
        # Do next: the live page's one ranked list, in the agent files' order, with one points number per action
        up = self.payload()["levels"]["quests"]
        rows = section.split('<div class="dn" tabindex="0" data-act="')[1:]
        self.assertEqual([r.split('"')[0] for r in rows], [q["id"] for q in up][:4])
        self.assertEqual(rows[0].split('"')[0], "A06")                            # the panel's best-case set leads, not last
        for row, q in zip(rows, up):
            cell = re.search(r'<div class="dn-p">(.*?)</div>', row).group(1)
            self.assertEqual(cell, "+%g" % q["points_expected"] if q["changes_a_score"] else "credibility", q["id"])
            self.assertEqual(len(re.findall(r"\+\d", re.sub(r"<[^>]+>", " ", row))), 1 if q["changes_a_score"] else 0)
            self.assertRegex(row, r'<div class="tiny sub">(To do|In progress)')  # a word beside the dot, not colour alone
        self.assertIn("Do next", text)
        self.assertNotIn("highest priority", text)
        self.assertIn('<th scope="col">Organisation</th>', section)
        self.assertIn('$("#staticSummary").hidden = true;', page)                 # hidden once the live page runs
        self.assertNotIn("__STATIC__", page)
        self.assertNotIn("Jordan", section)
        self.assertNotRegex(text, "[\u2013\u2014]| - ")

    def test_one_yardstick_keeps_the_mission_control_character(self):
        page, d = self.build()
        body, script = page.split('<script type="application/json"')
        # The owner keeps the flight, game and analyst vocabulary; only the misleading "best chance" label goes.
        for kept in ("Departed", "Altitude", "Flight level", "Offer zone", "Quests", "Badges", "Do next", "Start here",
                     "Biggest unlocks", "Verifiable record", "Progress you can trust", "Best role fit", "Done? Tell your agent",
                     "Expected by", "Do nothing", "What moves you", "Pending on this device"):
            self.assertIn(kept, page)
        self.assertNotIn("Your best chance", page)
        self.assertIn('Best match today</div>\n     <div class="best-v num"><span id="bestNum">57</span> <small>of 100</small>', body)
        # The marginal number appears only in the What if rail, labelled "with everything else on".
        blocks = [A.JS_CORE, A.JS_CHART, A.JS_HOME, A.JS_VIEWS, A.JS_LEVELS, A.JS_DETAIL]
        rail = A.JS_HOME[A.JS_HOME.index("function renderSwitches"):A.JS_HOME.index("function renderBottomBar")]
        self.assertGreater(rail.count("with everything else on"), 0)
        self.assertEqual(sum(b.count("with everything else on") for b in blocks), rail.count("with everything else on"))
        self.assertNotIn("actionLift", script)                    # the old "on top of the rest of the plan" number is gone
        # Phone: Do next comes straight after the headline status (strip, best match, level), before the chart.
        self.assertLess(body.index('id="level"'), body.index('id="nextIn"'))
        self.assertLess(body.index('id="nextIn"'), body.index('id="chartWrap"'))
        self.assertIn(".btn,.seg button,select{min-height:44px}", page)
        # One h1; tabs with aria-selected and aria-controls; every view keeps its tab, in a row that scrolls with a hint.
        self.assertEqual(len(re.findall(r"<h1[\s>]", page)), 1)
        self.assertIn('role="tab" id="tab-${v[0]}" aria-selected="${on}" aria-controls="v-${v[0]}"', script)
        self.assertNotIn('role="tab" aria-pressed', script)
        self.assertIn('<div class="hscroll"><div class="seg" id="viewSeg" role="tablist"', body)
        self.assertIn("scrollHint($(\"#viewSeg\"))", script)
        for v in ("Level up", "Organisations", "Path to the top band", "What moves you", "Roles", "SWOT and TOWS", "Plan", "Evidence", "Market"):
            self.assertIn('"%s"]' % v, script)
        # The made-up sample progress is a design preview, reachable only with ?preview=1.
        self.assertIn("$(\"#sampleRow\").hidden = !(D.meta.sample_allowed && PREVIEW);", script)
        # Internal ids stay off the main surfaces (the action pane keeps them): titles name another action by its short title.
        titles = {a["id"]: a["title"] for a in d["actions"]}
        self.assertEqual(titles["A08"], "Answer the notice period and non-compete question")
        self.assertIn("once \u201cFix the LinkedIn headline\u201d is done", titles["A06"])
        view = re.search(r'<section class="view on" id="v-level".*?</section>', body, re.S).group(0)
        view = re.sub(r'<span class="q-text">.*?</span>|data-act="[^"]*"', "", view)   # the note for the agent keeps the id
        self.assertNotRegex(view, r"\b[AEQ][0-9]{2}\b")

    def test_do_nothing_line_has_three_to_one_contrast(self):
        def lum(hexc):
            rgb = [int(hexc[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
            lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        def ratio(a, b):
            hi, lo = sorted((lum(a), lum(b)), reverse=True)
            return (hi + 0.05) / (lo + 0.05)
        light, dark = A.CSS.split(":root[data-theme=dark]")[0], A.CSS.split(":root[data-theme=dark]")[1].split("}")[0]
        for theme in (light, dark):
            tok = dict(re.findall(r"--(stop|z0|z1|card):(#[0-9a-f]{6})", theme))
            for bg in ("z0", "z1", "card"):
                self.assertGreaterEqual(ratio(tok["stop"], tok[bg]), 3.0, (tok, bg))

    def test_heatmap_ramp_reads_the_same_in_both_themes(self):
        # The caption must hold in light and dark: a higher score always stands out more from the card,
        # each step from 1 to 5 is visibly apart, and the number in the cell stays readable.
        def lum(hexc):
            rgb = [int(hexc[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
            lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        def ratio(a, b):
            hi, lo = sorted((lum(a), lum(b)), reverse=True)
            return (hi + 0.05) / (lo + 0.05)
        self.assertNotIn("darker is stronger", A.JS_VIEWS)
        self.assertIn("the more the cell stands out from the page", A.JS_VIEWS)
        light, dark = A.CSS.split(":root[data-theme=dark]")[0], A.CSS.split(":root[data-theme=dark]")[1].split("}")[0]
        for theme in (light, dark):
            tok = dict(re.findall(r"--(h[0-5]|hlt|hdt|card):(#[0-9a-f]{6})", theme))
            vs_card = [ratio(tok["h%d" % k], tok["card"]) for k in range(6)]
            self.assertEqual(vs_card, sorted(vs_card), tok)
            for k in range(1, 5):
                self.assertGreaterEqual(ratio(tok["h%d" % k], tok["h%d" % (k + 1)]), 1.25, (k, tok))
            for k in range(6):
                self.assertGreaterEqual(ratio(tok["h%d" % k], tok["hdt" if k >= 3 else "hlt"]), 4.5, (k, tok))

    def test_extension_fields_pass_through(self):
        for rel, fn in (("profile/evidence.json", lambda d: d["items"][0].update(x_original_id="G01")),
                        ("eval/judgements.json", lambda d: next(iter(d["roles"].values())).update(x_old="kept")),
                        ("campaign/plan.json", lambda d: d["actions"][1].update(x_old_rank=2)),
                        ("config.json", lambda d: d.update(x_note="mine"))):
            doc = H.load(os.path.join(self.ws, rel))
            fn(doc)
            H.save(os.path.join(self.ws, rel), doc)
        import score as S
        with mock.patch("sys.stdout"):
            self.assertEqual(S.main(["--workspace", self.ws, "--date", "2026-11-01"]), 0)
        self.build()
        import validate as V
        self.assertEqual(V.validate_workspace(self.ws)[0], [])


if __name__ == "__main__":
    unittest.main()
